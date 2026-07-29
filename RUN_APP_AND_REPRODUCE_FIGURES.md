# Run the app and reproduce figures

See `README_REPRODUCIBILITY.md` for installation and validation. Exact commands for every final figure are in `FIGURE_REPRODUCTION_COMMANDS.md`.

```bash
streamlit run app.py
python scripts/figures/generate_environmental_group_heatmaps.py --root .
python scripts/validation/compare_environmental_group_heatmaps.py --root .
```
