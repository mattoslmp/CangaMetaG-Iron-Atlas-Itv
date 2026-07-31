from __future__ import annotations

"""Keep KO/pathway labels on the complete ST8 source used by comparisons."""

MARKER = "CANGAMETAG_ST8_ENVIRONMENT_LABEL_V1 = 1"

if MARKER not in source:
  old = '''  counts_f["KO_pathway_label"] = np.where(
    show_ko_pathway_detail & ko_pathway.ne(""),
    ko_id + " | " + ko_pathway,
    ko_id,
  )'''
  new = old + '''
  source_ko_id = counts_selected_source["KO"].fillna("").astype(str).str.strip()
  source_ko_pathway = counts_selected_source["Metabolism"].fillna("Unclassified").astype(str).str.strip()
  counts_selected_source["KO_pathway_label"] = np.where(
    show_ko_pathway_detail & source_ko_pathway.ne(""),
    source_ko_id + " | " + source_ko_pathway,
    source_ko_id,
  )
  counts_selected_source.attrs["st8_include_undetected"] = bool(include_undetected_st8)'''
  if old in source:
    source = source.replace(old, new, 1)
  source += f"\n\n{MARKER}\n"
