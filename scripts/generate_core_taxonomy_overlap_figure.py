from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

BASE_DIR = Path(__file__).resolve().parents[1]
DATA = BASE_DIR / 'data' / 'st8_taxonomy_summary_by_group.csv'
OUT_DIR = BASE_DIR / 'outputs' / 'article_highres_figures'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def broad_group(name: str) -> str:
    text = str(name)
    if 'AMD' in text or 'Akron' in text or 'Richmond' in text:
        return 'AMD systems'
    if 'Lake Towuti' in text or 'Lake Matano' in text or 'Lake Superior' in text:
        return 'Ferruginous lakes/sediments'
    if 'Hydrothermal' in text:
        return 'Hydrothermal Fe-rich mats'
    if 'Control' in text:
        return 'Control reservoir'
    return 'Other/unassigned'

def sets_for_level(df: pd.DataFrame, level: str):
    work = df[(df['taxonomy_level'].eq(level)) & (pd.to_numeric(df['count_or_abundance'], errors='coerce').fillna(0) > 0)].copy()
    work['broad_group'] = work['ST8_group'].map(broad_group)
    keep = ['AMD systems', 'Ferruginous lakes/sediments', 'Hydrothermal Fe-rich mats']
    return {g: set(work.loc[work['broad_group'].eq(g), 'taxon'].dropna().astype(str)) for g in keep}, work[work['broad_group'].isin(keep)].copy()

def region_counts(sets):
    A = sets['AMD systems']; B = sets['Ferruginous lakes/sediments']; C = sets['Hydrothermal Fe-rich mats']
    return {
        'A_only': len(A - B - C),
        'B_only': len(B - A - C),
        'C_only': len(C - A - B),
        'AB': len((A & B) - C),
        'AC': len((A & C) - B),
        'BC': len((B & C) - A),
        'ABC': len(A & B & C),
    }

def core_top_table(work, level: str, n: int = 12):
    groups = ['AMD systems', 'Ferruginous lakes/sediments', 'Hydrothermal Fe-rich mats']
    core = set.intersection(*[set(work.loc[work['broad_group'].eq(g), 'taxon'].dropna().astype(str)) for g in groups])
    top = (work[work['taxon'].isin(core)]
           .groupby('taxon', as_index=False)['count_or_abundance'].sum()
           .sort_values('count_or_abundance', ascending=False)
           .head(n))
    top['short_taxon'] = top['taxon'].astype(str).str.split(':').str[-1]
    top['taxonomy_level'] = level
    return top

raw = pd.read_csv(DATA)
fig, axes = plt.subplots(2, 2, figsize=(14, 12), dpi=300)
plt.subplots_adjust(wspace=0.28, hspace=0.36)

circle_specs = [
    (0.40, 0.55, 0.30, '#D5E8FF', 'AMD systems'),
    (0.60, 0.55, 0.30, '#DFF3DC', 'Ferruginous lakes/sediments'),
    (0.50, 0.35, 0.30, '#FFE6CC', 'Hydrothermal Fe-rich mats'),
]
for ax, level in zip(axes[0], ['Phylum', 'Order']):
    sets, work = sets_for_level(raw, level)
    counts = region_counts(sets)
    ax.set_title(f'{level}-level taxonomic overlap', fontsize=13, fontweight='bold')
    for x, y, r, color, label in circle_specs:
        ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor='black', alpha=0.58, linewidth=1.4))
        ax.text(x, y + r + 0.055, label, ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(0.28, 0.60, str(counts['A_only']), ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.72, 0.60, str(counts['B_only']), ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.50, 0.18, str(counts['C_only']), ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.50, 0.64, str(counts['AB']), ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.39, 0.39, str(counts['AC']), ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.61, 0.39, str(counts['BC']), ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(0.50, 0.48, str(counts['ABC']), ha='center', va='center', fontsize=14, fontweight='bold', color='#8B0000')
    ax.text(0.50, 0.04, 'Center = taxa detected in all three Fe-rich environment classes', ha='center', va='center', fontsize=8)
    ax.set_xlim(0.08, 0.92); ax.set_ylim(0, 0.95); ax.set_axis_off()

# Core top taxa bars
for ax, level in zip(axes[1], ['Phylum', 'Order']):
    sets, work = sets_for_level(raw, level)
    top = core_top_table(work, level, n=12)
    ax.barh(top['short_taxon'][::-1], top['count_or_abundance'][::-1])
    ax.set_title(f'Top shared {level.lower()} taxa across Fe-rich groups', fontsize=12, fontweight='bold')
    ax.set_xlabel('Summed GTDB count/abundance across curated Fe-rich records')
    ax.tick_params(axis='y', labelsize=8)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

fig.suptitle('Supplementary Figure 22. Putative core taxonomic overlap across curated iron-rich environmental groups', fontsize=15, fontweight='bold', y=0.995)
fig.text(0.5, 0.01, 'Groups compared: AMD systems, ferruginous lake/sediment records and hydrothermal Fe-rich mats. Control and unassigned records are excluded from the core-overlap calculation.', ha='center', fontsize=9)

png = OUT_DIR / 'SuppFigure22_core_taxonomic_overlap_venn.png'
svg = OUT_DIR / 'SuppFigure22_core_taxonomic_overlap_venn.svg'
tif = OUT_DIR / 'SuppFigure22_core_taxonomic_overlap_venn.tiff'
fig.savefig(png, dpi=300, bbox_inches='tight')
fig.savefig(svg, dpi=300, bbox_inches='tight')
fig.savefig(tif, dpi=300, bbox_inches='tight')
# write source summary
rows = []
for level in ['Phylum','Order','Family']:
    sets, work = sets_for_level(raw, level)
    core = set.intersection(*sets.values())
    for taxon in sorted(core):
        rows.append({'taxonomy_level': level, 'core_taxon': taxon})
pd.DataFrame(rows).to_csv(OUT_DIR / 'source_SuppFigure22_core_taxonomic_overlap_venn.csv', index=False)
print(png)
print(svg)
print(tif)
