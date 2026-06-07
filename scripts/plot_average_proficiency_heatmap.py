#!/usr/bin/env python3
"""Build a California county heat map of average 2025 CAASPP proficiency.

The script starts from the CAASPP zip file committed in the repo, aggregates
school-level ELA and Math proficiency to counties, averages the two subjects,
and plots the result as a county choropleth.
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(REPO / ".matplotlib-cache"))

import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon


CAASPP_ZIP = REPO / "sb_ca2025_1_csv_v1.zip"
COUNTY_GEOJSON = REPO / "data" / "raw" / "geojson-counties-fips.json"
PROCESSED_DIR = REPO / "data" / "processed"
FIGURE_DIR = REPO / "outputs" / "figures"

SUBJECT_MAP = {"1": "ELA", "2": "Math"}

CA_COUNTY_FIPS = {
    "Alameda": "001",
    "Alpine": "003",
    "Amador": "005",
    "Butte": "007",
    "Calaveras": "009",
    "Colusa": "011",
    "Contra Costa": "013",
    "Del Norte": "015",
    "El Dorado": "017",
    "Fresno": "019",
    "Glenn": "021",
    "Humboldt": "023",
    "Imperial": "025",
    "Inyo": "027",
    "Kern": "029",
    "Kings": "031",
    "Lake": "033",
    "Lassen": "035",
    "Los Angeles": "037",
    "Madera": "039",
    "Marin": "041",
    "Mariposa": "043",
    "Mendocino": "045",
    "Merced": "047",
    "Modoc": "049",
    "Mono": "051",
    "Monterey": "053",
    "Napa": "055",
    "Nevada": "057",
    "Orange": "059",
    "Placer": "061",
    "Plumas": "063",
    "Riverside": "065",
    "Sacramento": "067",
    "San Benito": "069",
    "San Bernardino": "071",
    "San Diego": "073",
    "San Francisco": "075",
    "San Joaquin": "077",
    "San Luis Obispo": "079",
    "San Mateo": "081",
    "Santa Barbara": "083",
    "Santa Clara": "085",
    "Santa Cruz": "087",
    "Shasta": "089",
    "Sierra": "091",
    "Siskiyou": "093",
    "Solano": "095",
    "Sonoma": "097",
    "Stanislaus": "099",
    "Sutter": "101",
    "Tehama": "103",
    "Trinity": "105",
    "Tulare": "107",
    "Tuolumne": "109",
    "Ventura": "111",
    "Yolo": "113",
    "Yuba": "115",
}


def weighted_mean(group: pd.DataFrame) -> float:
    return (group["pct_met_above"] * group["tested_with_scores"]).sum() / group["tested_with_scores"].sum()


def load_caaspp_county_subject() -> pd.DataFrame:
    """Read CAASPP zip and aggregate school-level results by county and subject."""
    with zipfile.ZipFile(CAASPP_ZIP) as zf:
        with zf.open("sb_ca2025_1_csv_v1.txt") as f:
            caaspp = pd.read_csv(
                f,
                sep="^",
                encoding="latin1",
                dtype=str,
                usecols=[
                    "County Code",
                    "School Code",
                    "Test ID",
                    "Grade",
                    "Percentage Standard Met and Above",
                    "Total Students Tested with Scores",
                ],
            )
        with zf.open("sb_ca2025entities_csv.txt") as f:
            entities = pd.read_csv(
                f,
                sep="^",
                encoding="latin1",
                dtype=str,
                usecols=["County Code", "County Name"],
            )

    # CAASPP uses grade 13 as the all-grades summary row. Keep school-level
    # rows only, then limit to ELA and Math.
    caaspp = caaspp[
        (caaspp["School Code"] != "0000000")
        & (caaspp["Grade"] == "13")
        & (caaspp["Test ID"].isin(SUBJECT_MAP))
    ].copy()
    caaspp["County Code"] = caaspp["County Code"].astype(str).str.zfill(2)
    caaspp["subject"] = caaspp["Test ID"].map(SUBJECT_MAP)
    caaspp["pct_met_above"] = pd.to_numeric(caaspp["Percentage Standard Met and Above"], errors="coerce")
    caaspp["tested_with_scores"] = pd.to_numeric(caaspp["Total Students Tested with Scores"], errors="coerce")
    caaspp = caaspp.dropna(subset=["pct_met_above", "tested_with_scores"])

    county_names = entities[["County Code", "County Name"]].dropna().drop_duplicates()
    county_names["County Code"] = county_names["County Code"].astype(str).str.zfill(2)

    county_subject = (
        caaspp.groupby(["County Code", "subject"], as_index=False)
        .apply(lambda group: pd.Series({"county_pct_met_above": weighted_mean(group)}))
        .merge(county_names, on="County Code", how="left")
        .rename(columns={"County Code": "county_code", "County Name": "county_name"})
    )
    county_subject["county_fips"] = county_subject["county_name"].map(CA_COUNTY_FIPS)
    return county_subject


def build_average_proficiency() -> pd.DataFrame:
    county_subject = load_caaspp_county_subject()
    wide = (
        county_subject.pivot(index=["county_code", "county_name", "county_fips"], columns="subject", values="county_pct_met_above")
        .reset_index()
        .rename(columns={"ELA": "ela_pct_met_above", "Math": "math_pct_met_above"})
    )
    wide["avg_pct_met_above"] = wide[["ela_pct_met_above", "math_pct_met_above"]].mean(axis=1)
    wide = wide.sort_values("avg_pct_met_above", ascending=False)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    wide.to_csv(PROCESSED_DIR / "county_average_proficiency_heatmap.csv", index=False)
    return wide


def geometry_to_patches(feature: dict) -> list[Polygon]:
    geometry = feature["geometry"]
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return [Polygon(polygon[0], closed=True) for polygon in polygons]


def load_california_county_features() -> list[dict]:
    with COUNTY_GEOJSON.open() as f:
        geojson = json.load(f)
    return [feature for feature in geojson["features"] if str(feature.get("id", "")).startswith("06")]


def plot_heatmap(values: pd.DataFrame) -> None:
    features = load_california_county_features()
    value_lookup = dict(zip(values["county_fips"].astype(str).str.zfill(3), values["avg_pct_met_above"]))

    patches = []
    patch_values = []
    for feature in features:
        county_fips = feature["id"][2:]
        if county_fips not in value_lookup:
            continue
        feature_patches = geometry_to_patches(feature)
        patches.extend(feature_patches)
        patch_values.extend([value_lookup[county_fips]] * len(feature_patches))

    fig, ax = plt.subplots(figsize=(9, 10))
    norm = Normalize(vmin=min(patch_values), vmax=max(patch_values))
    collection = PatchCollection(
        patches,
        cmap="YlGnBu",
        norm=norm,
        edgecolor="white",
        linewidth=0.45,
    )
    collection.set_array(pd.Series(patch_values).to_numpy())
    ax.add_collection(collection)
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("California County CAASPP Proficiency, 2025\nAverage of ELA and Math", fontsize=15, pad=14)

    colorbar = fig.colorbar(collection, ax=ax, fraction=0.035, pad=0.01)
    colorbar.set_label("% Met/Exceeded CAASPP Standard")

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "county_average_proficiency_heatmap.png", dpi=200)
    plt.close(fig)


def main() -> None:
    values = build_average_proficiency()
    plot_heatmap(values)
    print(f"Saved processed data to {PROCESSED_DIR / 'county_average_proficiency_heatmap.csv'}")
    print(f"Saved heatmap to {FIGURE_DIR / 'county_average_proficiency_heatmap.png'}")


if __name__ == "__main__":
    main()
