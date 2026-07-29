#!/usr/bin/env python3
"""Final visual synchronization update for the Amazonian lateritic lakes app/article.

Run from the app root:
  python scripts/final_visual_sync_update_12Jun2026.py

This script regenerates selected publication figures using only packaged source tables.
No image is AI-generated. Every output has a paired source/audit CSV.
"""
from __future__ import annotations
from pathlib import Path
import textwrap
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from src.taxonomy_palette import build_palette, load_palette, save_palette
FIGDIR = BASE / "outputs" / "final_publication_figures"
AUDIT = BASE / "outputs" / "final_publication_audit_tables"
FIGDIR.mkdir(parents=True, exist_ok=True)
AUDIT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 13,
    "axes.titlesize": 19,
    "axes.labelsize": 16,
    "axes.labelweight": "bold",
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.fontsize": 12,
    "figure.dpi": 160,
    "savefig.dpi": 360,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

POS = "#1f9e89"  # Amazonian-enriched
NEG = "#d73027"  # external-enriched
BLUE = "#277da1"
PURPLE = "#7b2cbf"
ORANGE = "#f8961e"
GREEN = "#43aa8b"
DARK = "#111827"


def wrap(s, width=42):
    return "\n".join(textwrap.wrap(str(s), width=width, break_long_words=False))


def save(fig, name):
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(FIGDIR / f"{name}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_contrast_figure(source_csv, label_col, title, outname):
    df = pd.read_csv(source_csv).copy()
    df["display_label"] = df[label_col].astype(str) + " — " + df.get("category", "").astype(str)
    df["external_group_label"] = df["ST8_group"].astype(str) + " | " + df["data_layer"].astype(str)
    df["contrast_sign"] = np.where(df["log2_ratio_amazonia_vs_external"] >= 0,
                                    "Higher in Amazonian lateritic lakes",
                                    "Higher in external group")
    # balance top negatives and positives to avoid hiding Amazonian-enriched markers
    neg = df[df["log2_ratio_amazonia_vs_external"] < 0].nsmallest(10, "log2_ratio_amazonia_vs_external")
    pos = df[df["log2_ratio_amazonia_vs_external"] >= 0].nlargest(10, "log2_ratio_amazonia_vs_external")
    plot = pd.concat([neg, pos], ignore_index=True).drop_duplicates(subset=[label_col, "ST8_group", "data_layer"]) 
    plot = plot.sort_values("log2_ratio_amazonia_vs_external")
    plot["axis_label"] = plot.apply(lambda r: wrap(f"{r[label_col]} | {r['category']}", 44), axis=1)
    colors = [POS if v >= 0 else NEG for v in plot["log2_ratio_amazonia_vs_external"]]
    fig_h = max(10, 0.62 * len(plot) + 3)
    fig, ax = plt.subplots(figsize=(16, fig_h))
    ypos = np.arange(len(plot))
    ax.barh(ypos, plot["log2_ratio_amazonia_vs_external"], color=colors, edgecolor="white", linewidth=0.8)
    ax.set_yticks(ypos)
    ax.set_yticklabels(plot["axis_label"].tolist(), fontweight="bold")
    ax.axvline(0, color=DARK, linewidth=1.2, linestyle="--")
    ax.set_xlabel("Descriptive log2 ratio: Amazonian lateritic lakes vs selected external group/layer", fontweight="bold")
    ax.set_ylabel("Marker and pathway/category", fontweight="bold")
    ax.set_title(title, fontweight="bold", loc="left")
    for tick in ax.get_yticklabels() + ax.get_xticklabels():
        tick.set_fontweight("bold")
    xmax = max(abs(plot["log2_ratio_amazonia_vs_external"]).max(), 1)
    ax.set_xlim(-xmax * 1.35, xmax * 1.35)
    for y, (_, row) in enumerate(plot.iterrows()):
        val = row["log2_ratio_amazonia_vs_external"]
        def _abbr_group(s):
            s = str(s)
            s = s.replace("Main iron-rich/AMD group: Richmond Mine / Iron Mountain AMD", "Richmond AMD")
            s = s.replace("Additional AMD group: Akron / Pennsylvania-Ohio lab-enriched AMD", "Akron AMD")
            s = s.replace("Additional AMD group: Akron / Pennsylvania–Ohio lab-enriched AMD", "Akron AMD")
            s = s.replace("Ferruginous lake/sediment group: Lake Superior", "Lake Superior")
            s = s.replace("Ferruginous lake/sediment group: Lake Matano", "Lake Matano")
            s = s.replace("Control: Burr Oak Reservoir BO4", "Burr Oak BO4")
            s = s.replace("Other iron-rich / unassigned", "Other Fe")
            s = s.replace("Metatranscriptomics", "MT")
            s = s.replace("Metagenomics", "MG")
            s = s.replace("Combined assembly", "CA")
            return s
        lab = wrap(_abbr_group(row["external_group_label"]), 22)
        if val >= 0:
            x = val + 0.06 * xmax; ha = "left"; color = DARK
        else:
            x = val * 0.48; ha = "center"; color = "white"
        ax.text(x, y, lab, va="center", ha=ha, fontsize=8.5, fontweight="bold", color=color)
    # Method and input details are reported in the figure caption and audit CSV.
    ax.grid(False)
    fig.tight_layout()
    save(fig, outname)
    audit = plot.copy()
    audit["script"] = "scripts/final_visual_sync_update_12Jun2026.py"
    audit["input_table"] = str(Path(source_csv).relative_to(BASE))
    audit.to_csv(AUDIT / f"source_{outname}.csv", index=False)


def make_taxonomy_barplot(source_csv, title, outname, taxonomy_level, layer_filter=None, top=25):
    """Render one publication ST8 barplot with the canonical taxonomy palette.

    The chart follows the same definition used by the interactive app: the top
    N taxa are selected globally from the requested level/layer, every bar is
    renormalised to 100%, and the remainder is retained as ``Other taxa``.
    Colours are loaded from data/taxonomy_palette.json rather than assigned by
    plotting order.
    """
    df = pd.read_csv(source_csv, encoding="utf-8-sig", low_memory=False).copy()
    required = {"taxonomy_level", "ST8_group", "data_layer", "taxon", "count_or_abundance"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing ST8 taxonomy columns: {sorted(required.difference(df.columns))}")
    df = df[df["taxonomy_level"].astype(str).eq(str(taxonomy_level))].copy()
    if layer_filter:
        df = df[df["data_layer"].astype(str).eq(layer_filter)].copy()
    if df.empty:
        raise ValueError(f"No ST8 taxonomy rows for {taxonomy_level} / {layer_filter or 'all layers'}")
    df["count_or_abundance"] = pd.to_numeric(df["count_or_abundance"], errors="coerce").fillna(0).clip(lower=0)
    df["taxon"] = df["taxon"].fillna("Unclassified taxa").astype(str).str.strip().replace({"": "Unclassified taxa", "nan": "Unclassified taxa", "None": "Unclassified taxa", "Unknown": "Unclassified taxa"})
    if layer_filter:
        df["display_group"] = df["ST8_group"].astype(str)
    else:
        df["display_group"] = df["ST8_group"].astype(str) + " | " + df["data_layer"].astype(str)
    grouped = df.groupby(["display_group", "taxon"], as_index=False)["count_or_abundance"].sum()
    ranking = grouped.groupby("taxon")["count_or_abundance"].sum().sort_values(ascending=False)
    top_taxa = ranking.head(int(top)).index.tolist()
    grouped["display_taxon"] = np.where(grouped["taxon"].isin(top_taxa), grouped["taxon"], "Other taxa")
    plot = grouped.groupby(["display_group", "display_taxon"], as_index=False)["count_or_abundance"].sum()
    totals = plot.groupby("display_group")["count_or_abundance"].transform("sum").replace(0, np.nan)
    plot["relative_abundance_percent"] = (plot["count_or_abundance"] / totals * 100.0).fillna(0)
    order = top_taxa + (["Other taxa"] if "Other taxa" in set(plot["display_taxon"]) else [])
    palette = build_palette(order, load_palette())
    save_palette(palette)
    if len({palette[x] for x in order}) != len(order):
        raise RuntimeError("Repeated taxonomy colours detected in the canonical palette")
    groups = list(dict.fromkeys(plot["display_group"].astype(str).tolist()))
    x = np.arange(len(groups))
    bottom = np.zeros(len(groups), dtype=float)
    fig_w = max(18, min(44, 0.55 * len(groups) + 8))
    fig, ax = plt.subplots(figsize=(fig_w, 11.5))
    pivot = plot.pivot_table(index="display_group", columns="display_taxon", values="relative_abundance_percent", aggfunc="sum", fill_value=0).reindex(groups)
    for taxon in order:
        if taxon not in pivot.columns:
            continue
        vals = pivot[taxon].to_numpy(float)
        ax.bar(x, vals, bottom=bottom, label=taxon, color=palette[taxon], edgecolor="white", linewidth=0.35, width=0.86)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels([wrap(g, 26) for g in groups], rotation=55, ha="right", fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Relative abundance (%)", fontweight="bold")
    ax.set_xlabel("ST8 group" + ("" if layer_filter else " and omics layer"), fontweight="bold")
    ax.set_title(title, fontweight="bold", loc="left")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, title=taxonomy_level, fontsize=9, title_fontsize=10)
    ax.grid(False)
    fig.subplots_adjust(left=0.075, right=0.78, bottom=0.30, top=0.91)
    save(fig, outname)
    audit = plot.rename(columns={"display_taxon": "taxon"}).copy()
    audit["taxonomy_level"] = taxonomy_level
    audit["layer_filter"] = layer_filter or "all packaged layers"
    audit["top_n"] = int(top)
    audit["colour_hex"] = audit["taxon"].map(palette)
    audit["script"] = "scripts/final_visual_sync.py"
    audit["input_table"] = str(Path(source_csv).relative_to(BASE))
    audit.to_csv(AUDIT / f"source_{outname}.csv", index=False)


def make_common_taxa_heatmap():
    files = [
        ("Phylum", BASE/"outputs/st8_final_article_figures/source_ST8_Phylum_taxonomy_top20.csv"),
        ("Order", BASE/"outputs/st8_final_article_figures/source_ST8_Order_taxonomy_top25.csv"),
        ("Family", BASE/"outputs/st8_final_article_figures/source_ST8_Family_taxonomy_top25.csv"),
    ]
    pieces=[]
    for level, path in files:
        if path.exists():
            df=pd.read_csv(path)
            df["level"] = level
            pieces.append(df)
    if not pieces:
        return
    df=pd.concat(pieces, ignore_index=True)
    # common taxa: detected in at least three ST8 groups or layers
    det = df.groupby(["level","taxon"]).agg(n_groups=("ST8_group", "nunique"), n_layers=("data_layer", "nunique"), total=("count_or_abundance", "sum")).reset_index()
    common = det[(det["n_groups"]>=3) | ((det["n_groups"]>=2) & (det["n_layers"]>=2))].nlargest(40, "total")
    work = df.merge(common[["level","taxon"]], on=["level","taxon"])
    work["group_layer"] = work["ST8_group"].astype(str).str.replace("Additional AMD group: ", "", regex=False).str.replace("Ferruginous lake/sediment group: ", "", regex=False) + " | " + work["data_layer"].astype(str)
    pivot = work.pivot_table(index=["level","taxon"], columns="group_layer", values="count_or_abundance", aggfunc="sum", fill_value=0)
    # row z-score
    z = pivot.copy().astype(float)
    z = z.sub(z.mean(axis=1), axis=0).div(z.std(axis=1).replace(0, np.nan), axis=0).fillna(0)
    labels=[wrap(f"{lvl}: {tax}", 72) for lvl,tax in z.index]
    fig, ax = plt.subplots(figsize=(20, max(10, 0.34*len(labels)+4)))
    im = ax.imshow(z.values, aspect="auto", cmap="RdBu_r", vmin=-2.5, vmax=2.5)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontweight="bold")
    ax.set_xticks(np.arange(z.shape[1]))
    ax.set_xticklabels([wrap(c, 28) for c in z.columns], rotation=55, ha="right", fontweight="bold")
    ax.set_xlabel("ST8 group and omics layer", fontweight="bold")
    ax.set_ylabel("Common taxon", fontweight="bold")
    ax.set_title("Common taxa across iron-rich environments — Phylum, Order and Family", loc="left", fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.022, pad=0.02)
    cbar.set_label("Row z-score", fontweight="bold")
    fig.tight_layout()
    save(fig, "SupplementaryFigure32_common_taxa_heatmap")
    z.reset_index().to_csv(AUDIT / "source_SupplementaryFigure32_common_taxa_heatmap.csv", index=False)


def make_workflow():
    # Arrows only follow the sequence implemented by packaged scripts.
    steps = [
        ("Supplementary\nTables 1-9", "Input spreadsheets"),
        ("Kaiju CDS / FASTQ\ntaxonomy", "resultado.cds.* and resultado.kaiju.fastq.*"),
        ("KO and iron\nmarker matrices", "Supplementary Tables 4, 5 and 8"),
        ("ST8 Atlas\nrebuild", "rebuild_supplementary_table8_final.py"),
        ("Figure\nexport scripts", "final_visual_sync_update_12Jun2026.py + publication figure scripts"),
        ("Streamlit app\n+ article figures", "streamlit_app.py and final DOCX/PDF"),
    ]
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.axis("off")
    xs=np.linspace(0.05,0.95,len(steps))
    y=0.55
    box_colors=["#e0fbfc", "#98c1d9", "#ee6c4d", "#ffd166", "#06d6a0", "#cdb4db"]
    for i,(x,(title,sub)) in enumerate(zip(xs,steps)):
        rect=FancyBboxPatch((x-0.075,y-0.16),0.15,0.32, boxstyle="round,pad=0.02,rounding_size=0.03", linewidth=2, edgecolor="#1f2937", facecolor=box_colors[i], alpha=0.95)
        ax.add_patch(rect)
        ax.text(x,y+0.055,title,ha="center",va="center",fontweight="bold",fontsize=13,color="#111827")
        ax.text(x,y-0.075,wrap(sub,22),ha="center",va="center",fontsize=9.5,color="#111827")
        if i < len(xs)-1:
            arr=FancyArrowPatch((x+0.085,y),(xs[i+1]-0.085,y), arrowstyle="-|>", mutation_scale=22, linewidth=2.2, color="#3a0ca3")
            ax.add_patch(arr)
    ax.text(0.5,0.92,"Iron-rich Environment Metagenomic Atlas workflow",ha="center",va="center",fontsize=20,fontweight="bold",color="#111827")
    ax.text(0.5,0.12,"Arrows show only the implemented direction used by the packaged scripts: source tables -> taxonomic/KO matrices -> ST8 rebuild -> figure export -> app/article synchronization.",ha="center",va="center",fontsize=12,color="#111827")
    fig.tight_layout()
    save(fig,"SupplementaryFigure22_atlas_workflow_refined")
    save(fig,"SupplementaryFigure30_atlas_workflow_refined")
    pd.DataFrame([{"step":i+1,"node":t,"input_or_script":s,"direction":"left_to_right"} for i,(t,s) in enumerate(steps)]).to_csv(AUDIT/"source_SupplementaryFigure22_atlas_workflow_refined.csv",index=False)


def make_figure6_enriched():
    path = BASE/"outputs/final_publication_statistics/Figure6_top_taxa_LFC_source.csv"
    if not path.exists(): return
    df=pd.read_csv(path)
    df["LFC"] = pd.to_numeric(df["LFC"], errors="coerce")
    df["display"] = df["Taxon"].astype(str).map(lambda x: wrap(x, 56))
    df["comparison_annotation"] = df["Comparison_label"].astype(str)
    df=df.sort_values("LFC")
    colors=np.where(df["LFC"]>=0, POS, NEG)
    fig,ax=plt.subplots(figsize=(18,max(10,0.33*len(df)+2)))
    ax.barh(df["display"], df["LFC"], color=colors, edgecolor="white")
    ax.axvline(0,color=DARK,ls="--")
    xmax=max(abs(df["LFC"]).max(),1)
    ax.set_xlim(-xmax*1.4, xmax*1.4)
    for y,(_,r) in enumerate(df.iterrows()):
        val=r["LFC"]
        ax.text(val+(0.05*xmax if val>=0 else -0.05*xmax), y, r["comparison_annotation"], ha="left" if val>=0 else "right", va="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("log2 fold-change (LFC)", fontweight="bold")
    ax.set_ylabel("Taxon", fontweight="bold")
    ax.set_title("Top enriched taxa by comparison", loc="left", fontweight="bold")
    for tick in ax.get_xticklabels()+ax.get_yticklabels(): tick.set_fontweight("bold")
    fig.tight_layout()
    save(fig,"Figure6_taxon_log2FC_comparison_labeled")
    df.to_csv(AUDIT/"source_Figure6_taxon_log2FC_comparison_labeled.csv",index=False)


def main():
    src10 = BASE/"outputs/nature_isme_figures/source_Figure10_ST8_all_KO_descriptive_contrast_Nature_ISME.csv"
    src11 = BASE/"outputs/nature_isme_figures/source_Figure11_ST8_iron_KO_descriptive_contrast_Nature_ISME.csv"
    if src10.exists(): make_contrast_figure(src10,"KO","Strongest all-KO/metabolism contrasts — external group named at bar tip","Figure10_all_KO_descriptive_contrasts_labeled")
    if src11.exists(): make_contrast_figure(src11,"Function Id","Strongest iron-metabolism contrasts — external group named at bar tip","Figure11_iron_KO_descriptive_contrasts_labeled")
    make_figure6_enriched()
    st8_taxonomy = BASE / "tables" / "st8_taxonomy_summary_by_group.csv"
    tax_specs = [
        ("Phylum", "GTDB phylum taxonomy by group — combined layers", "SupplementaryFigure14_GTDB_phylum_combined_bold", None, 20),
        ("Phylum", "GTDB phylum taxonomy by group — metagenomics", "SupplementaryFigure18_GTDB_phylum_metagenomics_bold", "Metagenomics", 20),
        ("Phylum", "GTDB phylum taxonomy by group — metatranscriptomics", "SupplementaryFigure19_GTDB_phylum_metatranscriptomics_bold", "Metatranscriptomics", 20),
        ("Order", "GTDB order taxonomy by group — combined layers", "SupplementaryFigure20_GTDB_order_combined_bold", None, 25),
        ("Order", "GTDB order taxonomy by group — metagenomics", "SupplementaryFigure21_GTDB_order_metagenomics_bold", "Metagenomics", 25),
        ("Order", "GTDB order taxonomy by group — metatranscriptomics", "SupplementaryFigure22_GTDB_order_metatranscriptomics_bold", "Metatranscriptomics", 25),
        ("Family", "GTDB family taxonomy by group — combined layers", "SupplementaryFigure23_GTDB_family_combined_bold", None, 25),
        ("Family", "GTDB family taxonomy by group — metagenomics", "SupplementaryFigure24_GTDB_family_metagenomics_bold", "Metagenomics", 25),
        ("Family", "GTDB family taxonomy by group — metatranscriptomics", "SupplementaryFigure25_GTDB_family_metatranscriptomics_bold", "Metatranscriptomics", 25),
    ]
    for level,title,out,layer,top in tax_specs:
        if st8_taxonomy.exists():
            make_taxonomy_barplot(st8_taxonomy, title, out, taxonomy_level=level, layer_filter=layer, top=top)
    make_common_taxa_heatmap()
    make_workflow()
    print(f"Wrote figures to {FIGDIR}")
    print(f"Wrote audit tables to {AUDIT}")

if __name__ == "__main__":
    main()
