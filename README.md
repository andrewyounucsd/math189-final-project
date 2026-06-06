# math189-final-project

## Average CAASPP Proficiency Heat Map

This repo includes a reproducible script for generating a California county heat map of 2025 CAASPP proficiency, averaged across ELA and Math.

## Repository Layout

- `math189_final_project.ipynb`: main analysis notebook.
- `featureSelection.ipynb`: feature-selection/modeling notebook.
- `scripts/`: reusable scripts for reproducible figure generation.
- `data/raw/`: supporting raw assets that are not already in the repo root.
- `data/processed/`: generated cleaned/aggregated CSV files.
- `outputs/figures/`: generated plots and report figures.
- `requirements.txt`: Python dependencies needed to run the notebook/scripts.

### Inputs

- `sb_ca2025_1_csv_v1.zip`: CAASPP school-level testing data.
- `data/raw/geojson-counties-fips.json`: U.S. county boundary GeoJSON used to draw California county shapes. This file is from Plotly's public county FIPS GeoJSON dataset and is stored locally so the script can run without downloading map data.

### Data Processing Steps

The script `scripts/plot_average_proficiency_heatmap.py` performs the following steps:

1. Opens `sb_ca2025_1_csv_v1.zip`.
2. Reads `sb_ca2025_1_csv_v1.txt`, the CAASPP score file.
3. Reads `sb_ca2025entities_csv.txt`, the entity lookup file containing county names.
4. Keeps school-level rows only by excluding `School Code == 0000000`.
5. Keeps `Grade == 13`, which is the all-grades summary row.
6. Keeps only `Test ID == 1` for ELA and `Test ID == 2` for Math.
7. Converts `% Met/Exceeded Standard` and tested-student counts into numeric columns.
8. Aggregates school-level scores to county-subject scores using tested-student weighted averages.
9. Pivots counties into ELA and Math columns.
10. Computes `avg_pct_met_above` as the average of county ELA and Math proficiency.
11. Maps county names to county FIPS codes.
12. Joins values to California county geometries and plots the heat map.

### Outputs

- `data/processed/county_average_proficiency_heatmap.csv`
- `outputs/figures/county_average_proficiency_heatmap.png`

### Reproduce

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the heat map:

```bash
python3 scripts/plot_average_proficiency_heatmap.py
```

### Note

This is a 2025 proficiency-level heat map. It does not show improvement over time because only one CAASPP year is used here.
