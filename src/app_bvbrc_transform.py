from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


mag_link_anchor = '''    bins_f["GBK_available"] = bins_f["MAG"].map(lambda x: "yes" if genbank_path_for_mag(x, annotation_folder(x)) else "no")
    bins_f = sort_mags_table(bins_f)
'''
mag_link_replacement = '''    bins_f["GBK_available"] = bins_f["MAG"].map(lambda x: "yes" if genbank_path_for_mag(x, annotation_folder(x)) else "no")

    def _public_bvbrc_url_for_table(mag_value):
      record = public_link_for_mag(mag_value)
      if isinstance(record, dict):
        genome_id = str(record.get("BV-BRC Genome ID", "")).strip()
        if genome_id:
          return bvbrc_genome_url_from_id(genome_id)
        return str(record.get("Workspace MAG URL", "")).strip()
      return str(record or "").strip()

    bins_f["BV-BRC link"] = bins_f["MAG"].map(_public_bvbrc_url_for_table)
    bins_f = sort_mags_table(bins_f)
'''
source = replace_once(source, mag_link_anchor, mag_link_replacement, "per-MAG BV-BRC links")
