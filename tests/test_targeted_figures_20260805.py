from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "final_publication_derived"
OUTPUT = ROOT / "outputs" / "final_publication_figures"
VALIDATION = ROOT / "validation" / "targeted_figures_20260805"
STEMS = [
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
    "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
    "Figure4_taxonomic_bacteria_genus_profiles",
    "Figure5_taxonomic_archaea_genus_profiles",
    "SupplementaryFigure6_MAG_bubble_original",
    "SupplementaryFigure18_RDA_and_physicochemical_heatmap",
    "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct",
    "SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct",
    "SupplementaryFigure59_Taxonomy_Bacteria_Genus_individual_samples_barplot_100pct",
    "SupplementaryFigure61_Taxonomy_Archaea_Genus_individual_samples_barplot_100pct",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TargetedFigureTests(unittest.TestCase):
    def test_canonical_scripts_and_modules_parse(self) -> None:
        paths = [
            ROOT / "scripts" / "generate_targeted_figures_20260805.py",
            ROOT / "scripts" / "generate_final_domain_taxonomy_figures.py",
            ROOT / "scripts" / "generate_supplementary_figures_6_18.py",
            ROOT / "scripts" / "generate_taxonomy_supplementary_figures.py",
            ROOT / "scripts" / "update_targeted_manifest_20260805.py",
            ROOT / "src" / "article_taxonomy.py",
            ROOT / "src" / "taxonomy_normalization.py",
            ROOT / "src" / "app_taxonomy_article_alignment_transform.py",
            ROOT / "src" / "app_other_taxa_percentage_label_transform.py",
        ]
        for path in paths:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_transform_chain_compiles_without_rebuilding_app(self) -> None:
        source = (ROOT / "app_core.py").read_text(encoding="utf-8")
        app_text = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("app_taxonomy_article_alignment_transform.py", app_text)
        self.assertIn("app_other_taxa_percentage_label_transform.py", app_text)
        self.assertNotIn("streamlit_app.py", app_text)
        self.assertGreater(len(source), 1000)

    def test_all_target_formats_exist_and_are_high_resolution(self) -> None:
        for stem in STEMS:
            for extension in ("png", "pdf", "svg"):
                path = OUTPUT / f"{stem}.{extension}"
                self.assertTrue(path.exists() and path.stat().st_size > 0, path)
            with Image.open(OUTPUT / f"{stem}.png") as image:
                self.assertGreaterEqual(min(image.info.get("dpi", (0, 0))), 599.0)

    def test_strict_lt1_unclassified_and_other_traceability(self) -> None:
        for domain in ("Bacteria", "Archaea"):
            for rank in ("Phylum", "Genus"):
                matrix = pd.read_csv(DATA / f"{domain}_{rank}_strict_lt1_display_source.csv", index_col=0)
                self.assertIn("Unclassified", matrix.index)
                self.assertTrue(((matrix.sum(axis=0) - 100.0).abs() <= 1e-8).all())
        audit = pd.read_csv(DATA / "TAXONOMY_STRICT_LT1_ROW_AUDIT_20260805.csv")
        self.assertTrue(audit["validation_status"].eq("PASS").all())
        self.assertFalse(audit.loc[audit["is_unclassified"], "grouped_into_other"].any())
        self.assertTrue((audit.loc[audit["grouped_into_other"], "original_relative_abundance"] < 1.0).all())

    def test_static_interactive_parity(self) -> None:
        parity = pd.read_csv(VALIDATION / "STATIC_INTERACTIVE_TAXONOMY_PARITY_20260805.csv")
        self.assertEqual(len(parity), 4)
        self.assertTrue(parity["validation_status"].eq("PASS").all())
        self.assertTrue(parity["values_identical"].all())

    def test_s6_complete_catalogue_and_audit(self) -> None:
        source = pd.read_csv(DATA / "SupplementaryFigure6_MAG_bubble_original_source.csv")
        self.assertEqual(source["MAG_ID"].nunique(), 49)
        self.assertTrue((source.groupby("MAG_ID")["lake_season_group"].nunique() == 8).all())
        audit = pd.read_csv(VALIDATION / "SupplementaryFigure6_MAG_audit.csv")
        self.assertTrue(audit["validation_status"].eq("PASS").all())

    def test_s18_frozen_matrix_and_external_colorbar(self) -> None:
        before = DATA / "SupplementaryFigure17_physicochemical_row_zscore_source.csv"
        after = DATA / "SupplementaryFigure18_RDA_and_physicochemical_heatmap_source.csv"
        self.assertEqual(sha256(before), sha256(after))
        audit = json.loads((VALIDATION / "SupplementaryFigure18_frozen_data_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["layout_validation"]["dedicated_colorbar_axis"])
        self.assertTrue(audit["layout_validation"]["colorbar_outside_heatmap"])
        self.assertEqual(audit["Bacteria"]["seed"], 42)
        self.assertEqual(audit["Archaea"]["permutations"], 999)

    def test_existing_taxonomy_ui_has_exact_hover_and_no_top_n(self) -> None:
        article = (ROOT / "src" / "article_taxonomy.py").read_text(encoding="utf-8")
        alignment = (ROOT / "src" / "app_taxonomy_article_alignment_transform.py").read_text(encoding="utf-8")
        labels = (ROOT / "src" / "app_other_taxa_percentage_label_transform.py").read_text(encoding="utf-8")
        self.assertIn("collapse_below_threshold", article)
        self.assertIn("Original relative abundance", article)
        self.assertIn("Unclassified", article)
        self.assertNotIn("Top-14", alignment)
        self.assertNotIn("st.slider", alignment)
        self.assertIn("Other taxa (<1%)", alignment)
        self.assertIn("_OTHER_TAXA_THRESHOLD_PERCENT = 1.0", labels)


if __name__ == "__main__":
    unittest.main()
