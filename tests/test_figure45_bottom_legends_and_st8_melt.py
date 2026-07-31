from __future__ import annotations

from pathlib import Path
import runpy

import pandas as pd

from src.article_frozen_taxonomy_static_v3 import materialize_frozen_article_static_v3
from src.st8_biomarker_heatmap import filter_detected_markers


ROOT = Path(__file__).resolve().parents[1]


def test_st8_filtered_dataframe_attrs_are_safe_for_pandas_melt() -> None:
  frame = pd.DataFrame({
    "KO": ["K00001", "K00002"],
    "Metabolism": ["A", "B"],
    "KO description": ["first", "second"],
    "AM.P1.D": [3, 1],
    "AM.P1.R": [0, 2],
  })
  display, summary, row_audit = filter_detected_markers(
    frame,
    ["AM.P1.D", "AM.P1.R"],
    scope_name="test",
  )

  assert len(summary) == 1
  assert len(row_audit) == 2
  assert not any(isinstance(value, pd.DataFrame) for value in display.attrs.values())

  melted = display.melt(
    id_vars=["KO", "Metabolism", "KO description"],
    value_vars=["AM.P1.D", "AM.P1.R"],
    var_name="sample",
    value_name="count",
  )
  assert len(melted) == 4
  assert melted["count"].sum() == 6


def test_runtime_melt_guard_clears_preexisting_complex_attrs() -> None:
  source = '''from __future__ import annotations
import pandas as pd


def _long_marker_counts_for_boxplot(frame):
  return frame.melt(
    id_vars=["KO"],
    value_vars=["AM.P1.D", "AM.P1.R"],
    var_name="sample",
    value_name="count",
  )

page_handlers = {}
selected_page = "none"
page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_dataframe_attrs_melt_guard_transform.py"),
    init_globals={"source": source},
  )["source"]
  namespace: dict[str, object] = {}
  exec(compile(transformed, "synthetic_melt_guard.py", "exec"), namespace, namespace)

  frame = pd.DataFrame({"KO": ["K00001"], "AM.P1.D": [1], "AM.P1.R": [2]})
  frame.attrs["nested_dataframe"] = pd.DataFrame({"x": [1]})
  result = namespace["_long_marker_counts_for_boxplot"](frame)
  assert isinstance(result, pd.DataFrame)
  assert result["count"].tolist() == [1, 2]
  assert result.attrs == {}


def test_figure45_app_transform_places_legends_below_entire_figure() -> None:
  source = '''from __future__ import annotations


def article_frozen_taxonomy_figure(domain):
  return None, {}

page_handlers = {}
selected_page = "none"
page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_figure45_bottom_legend_transform.py"),
    init_globals={"source": source},
  )["source"]
  assert '"y": -0.30' in transformed
  assert '"y": -0.105' in transformed
  assert '"legend_below_entire_figure": True' in transformed
  assert "materialize_frozen_article_static_v3" in transformed
  compile(transformed, "synthetic_figure45_legend.py", "exec")


def test_static_and_canonical_script_use_bottom_legend_v3() -> None:
  static_source = (ROOT / "src" / "article_frozen_taxonomy_static_v3.py").read_text(encoding="utf-8")
  script_source = (
    ROOT / "scripts" / "final_publication_figures" /
    "02_05_generate_final_taxonomy_figures.py"
  ).read_text(encoding="utf-8")

  assert "Dedicated bottom band" in static_source
  assert "ax_c.legend(" not in static_source
  assert "ax_d.legend(" not in static_source
  assert 'bbox_to_anchor=(0.075, 0.145)' in static_source
  assert 'bbox_to_anchor=(0.96, 0.145)' in static_source
  assert 'bbox_to_anchor=(0.5, 0.018)' in static_source
  assert "article_frozen_taxonomy_static_v3" in script_source
  assert "all legends in a dedicated band below all four panels" in script_source


def test_static_v3_generates_both_article_svgs_with_bottom_legends(tmp_path: Path) -> None:
  for domain, expected_stem in (
    ("Bacteria", "Figure4_taxonomic_bacteria_genus_profiles"),
    ("Archaea", "Figure5_taxonomic_archaea_genus_profiles"),
  ):
    svg_path = materialize_frozen_article_static_v3(domain, tmp_path)
    assert svg_path.name == f"{expected_stem}.svg"
    assert svg_path.parent.name == "frozen_article_taxonomy_static_v3_bottom_legends"
    text = svg_path.read_text(encoding="utf-8")
    assert "Bray-Curtis NMDS" in text
    assert "RDA biplot" in text
    assert "Lake / season" in text
    assert "RDA vectors" in text
    assert "Environmental variable" in text
    assert "Representative genus vector" in text
    assert svg_path.stat().st_size > 100000
