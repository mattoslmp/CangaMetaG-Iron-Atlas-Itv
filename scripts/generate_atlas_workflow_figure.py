from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / 'outputs' / 'article_highres_figures'
OUT_DIR.mkdir(parents=True, exist_ok=True)

boxes = [
  (0.05, 0.78, 0.25, 0.12, '1. Input datasets', 'Supplementary Tables 1–9\nCurated Atlas metadata\nBV-BRC / IMG/M support files'),
  (0.38, 0.78, 0.24, 0.12, '2. Harmonization', 'Sample IDs, KO tables,\npathway links, GTDB taxonomy,\nverified Amazonian coordinates'),
  (0.70, 0.78, 0.25, 0.12, '3. Core atlas tables', 'Iron-Rich Metagenomic Atlas\nall KO / iron KO matrices\nmetadata and study references'),
  (0.06, 0.48, 0.26, 0.14, '4. Analyses', 'Taxonomic profiles\nDifferential abundance\nKO/iron contrasts\nmarker abundance summaries'),
  (0.38, 0.48, 0.24, 0.14, '5. Environmental integration', 'Coordinates and dates\nGoogle/coordinate-check maps\nNASA POWER / CHIRPS / SoilGrids\nSentinel / Earthdata'),
  (0.70, 0.48, 0.25, 0.14, '6. Atlas outputs', 'Interactive app panels\nDownloadable linked tables\nHigh-readability heatmaps\npublication figures'),
  (0.24, 0.18, 0.26, 0.14, '7. Manuscript figures', 'Main Figures 1–11\nSupplementary Figures 1–22\nPNG / SVG / TIFF exports'),
  (0.56, 0.18, 0.28, 0.14, '8. Reproducibility', 'Python scripts in scripts/\nModules in src/\nFigure manifest + execution commands'),
]

fig = plt.figure(figsize=(15, 10), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off()
ax.text(0.5, 0.965, 'Supplementary Figure 22. Workflow of the Iron-Rich Environment Metagenomic Atlas app and figure-generation pipeline',
        ha='center', va='top', fontsize=16, fontweight='bold')
ax.text(0.5, 0.935, 'All elements are generated directly from the curated supplementary tables and app code; no fabricated scientific data are introduced in the workflow.',
        ha='center', va='top', fontsize=10)

face = '#E8F5F3'
edge = '#0E6251'
for x, y, w, h, title, body in boxes:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.012,rounding_size=0.02', linewidth=2.0, edgecolor=edge, facecolor=face))
    ax.text(x + w / 2, y + h * 0.70, title, ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(x + w / 2, y + h * 0.36, body, ha='center', va='center', fontsize=10)

arrows = [
    ((0.30, 0.84), (0.38, 0.84)), ((0.62, 0.84), (0.70, 0.84)),
    ((0.19, 0.78), (0.19, 0.62)), ((0.50, 0.78), (0.50, 0.62)), ((0.82, 0.78), (0.82, 0.62)),
    ((0.32, 0.55), (0.38, 0.55)), ((0.62, 0.55), (0.70, 0.55)),
    ((0.19, 0.48), (0.32, 0.32)), ((0.50, 0.48), (0.37, 0.32)), ((0.82, 0.48), (0.70, 0.32)),
    ((0.50, 0.48), (0.70, 0.32)), ((0.50, 0.25), (0.56, 0.25)),
]
for (x1, y1), (x2, y2) in arrows:
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=18, linewidth=2, color='#1565C0'))

ax.text(0.5, 0.06, 'Key scripts: rebuild_supplementary_table8_final.py | generate_article_figures_high_readability.py | generate_st8_final_article_figures.py | export_publication_figure_formats.py',
        ha='center', va='center', fontsize=10)

png = OUT_DIR / 'SuppFigure22_Iron_Rich_Atlas_workflow.png'
svg = OUT_DIR / 'SuppFigure22_Iron_Rich_Atlas_workflow.svg'
tif = OUT_DIR / 'SuppFigure22_Iron_Rich_Atlas_workflow.tiff'
fig.savefig(png, dpi=300, bbox_inches='tight')
fig.savefig(svg, dpi=300, bbox_inches='tight')
fig.savefig(tif, dpi=300, bbox_inches='tight')
print(png)
print(svg)
print(tif)
