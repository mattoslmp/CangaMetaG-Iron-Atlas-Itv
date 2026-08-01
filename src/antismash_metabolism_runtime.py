from __future__ import annotations

"""Evidence-focused antiSMASH BGC summary for the public app.

The module reads the packaged antiSMASH region GenBank files directly. It does
not rerun antiSMASH, change predictions, or infer a known compound when the
source output does not provide one.
"""

from pathlib import Path
import base64
import html
import re

import pandas as pd

from src.antismash_viewer import discover_antismash_runs


IRON_METAL_PATTERNS = {
  "siderophore": "Direct siderophore prediction: candidate Fe(III) acquisition/chelation BGC.",
  "metallophore": "Direct metallophore annotation: candidate metal-chelation BGC.",
  "ferric": "Ferric-iron annotation detected inside the BGC region.",
  "ferrous": "Ferrous-iron annotation detected inside the BGC region.",
  "iron": "Iron-related annotation detected inside the BGC region.",
  "heme": "Heme-related annotation detected inside the BGC region.",
  "haem": "Heme-related annotation detected inside the BGC region.",
  "copper": "Copper-related annotation detected inside the BGC region.",
  "zinc": "Zinc-related annotation detected inside the BGC region.",
  "nickel": "Nickel-related annotation detected inside the BGC region.",
  "cobalt": "Cobalt-related annotation detected inside the BGC region.",
  "manganese": "Manganese-related annotation detected inside the BGC region.",
  "molybden": "Molybdenum-related annotation detected inside the BGC region.",
  "tungsten": "Tungsten-related annotation detected inside the BGC region.",
}

CARBON_SKELETON_TYPES = {
  "t1pks", "t2pks", "t3pks", "transat-pks", "transatpks", "pks-like",
  "nrps", "nrps-like", "terpene", "arylpolyene", "resorcinol", "ladderane",
  "fatty_acid", "pufa", "hgle-ks", "betalactone", "butyrolactone",
  "saccharide", "phosphonate", "ectoine", "ripp-like", "lanthipeptide",
  "lassopeptide", "thiopeptide", "ranthipeptide", "redox-cofactor",
}

CENTRAL_CARBON_TERMS = {
  "carbon fixation", "rubisco", "ribulose-bisphosphate", "carboxysome",
  "methane", "methanol", "methylotroph", "acetyl-coa", "malonyl-coa",
  "propionyl-coa", "carbohydrate", "glycolysis", "gluconeogenesis",
}

LITERATURE = {
  "antismash": "Blin et al. 2023, antiSMASH 7.0, DOI: 10.1093/nar/gkad344.",
  "siderophore": "Barry & Challis 2009, siderophore biosynthesis, DOI: 10.1016/j.cbpa.2009.03.008; Chi et al. 2016, microbial iron acquisition, DOI: 10.1007/s10534-016-9949-x.",
  "terpene": "Helfrich et al. 2019, bacterial terpene biosynthesis, DOI: 10.3762/bjoc.15.283.",
  "pks": "Jenke-Kodama et al. 2005, bacterial PKS carbon-skeleton biosynthesis, DOI: 10.1093/molbev/msi193.",
}


def _feature_blocks(text: str, feature_name: str) -> list[str]:
  pattern = re.compile(
    rf"^\s{{5}}{re.escape(feature_name)}\s+.*?(?=^\s{{5}}\S|^ORIGIN|\Z)",
    flags=re.MULTILINE | re.DOTALL,
  )
  return pattern.findall(text)


def _qualifiers(block: str, name: str) -> list[str]:
  return [value.strip() for value in re.findall(rf'/{re.escape(name)}="([^"]*)"', block)]


def _location(block: str) -> tuple[int, int, int]:
  header = block.splitlines()[0] if block else ""
  numbers = [int(value) for value in re.findall(r"\d+", header)]
  if len(numbers) < 2:
    return 0, 1, 1
  start, end = min(numbers), max(numbers)
  strand = -1 if "complement" in header else 1
  return start, end, strand


def _region_products(text: str) -> list[str]:
  products: list[str] = []
  for feature in ("region", "cand_cluster", "protocluster"):
    for block in _feature_blocks(text, feature):
      products.extend(_qualifiers(block, "product"))
  return list(dict.fromkeys(product for product in products if product))


def _cds_records(text: str) -> list[dict[str, object]]:
  records: list[dict[str, object]] = []
  for block in _feature_blocks(text, "CDS"):
    start, end, strand = _location(block)
    if end <= start:
      continue
    gene_kind = (_qualifiers(block, "gene_kind") or [""])[0]
    product = (_qualifiers(block, "product") or [""])[0]
    locus = (_qualifiers(block, "locus_tag") or _qualifiers(block, "gene") or [""])[0]
    records.append({
      "start": start,
      "end": end,
      "strand": strand,
      "gene_kind": gene_kind,
      "product": product,
      "locus_tag": locus,
    })
  return records


def _cluster_svg_data_uri(cds: list[dict[str, object]], title: str) -> str:
  width, height = 760, 105
  if not cds:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="white"/><text x="18" y="55" font-family="Arial" font-size="18">No CDS geometry available</text></svg>'
  else:
    min_pos = min(int(row["start"]) for row in cds)
    max_pos = max(int(row["end"]) for row in cds)
    span = max(1, max_pos - min_pos)
    shapes: list[str] = []
    for row in cds:
      x1 = 18 + 724 * (int(row["start"]) - min_pos) / span
      x2 = 18 + 724 * (int(row["end"]) - min_pos) / span
      x2 = max(x1 + 5, x2)
      kind = str(row.get("gene_kind", "")).casefold()
      product = str(row.get("product", "")).casefold()
      if "biosynthetic" in kind:
        color = "#C2410C"
      elif "transport" in kind or "transport" in product:
        color = "#2563EB"
      elif "regulatory" in kind or "regulat" in product:
        color = "#CA8A04"
      else:
        color = "#64748B"
      y, h = 43, 24
      if int(row.get("strand", 1)) >= 0:
        points = f"{x1},{y} {max(x1, x2-8)},{y} {x2},{y+h/2} {max(x1, x2-8)},{y+h} {x1},{y+h}"
      else:
        points = f"{x2},{y} {min(x2, x1+8)},{y} {x1},{y+h/2} {min(x2, x1+8)},{y+h} {x2},{y+h}"
      tooltip = html.escape(str(row.get("locus_tag", "")) + " | " + str(row.get("product", "")))
      shapes.append(f'<polygon points="{points}" fill="{color}" stroke="#0F172A" stroke-width="0.7"><title>{tooltip}</title></polygon>')
    safe_title = html.escape(title[:90])
    svg = (
      f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
      '<rect width="100%" height="100%" fill="white"/>'
      f'<text x="18" y="24" font-family="Arial" font-size="15" font-weight="bold">{safe_title}</text>'
      + "".join(shapes)
      + '<text x="18" y="94" font-family="Arial" font-size="11">orange: biosynthetic | blue: transport | yellow: regulatory | gray: other CDS</text>'
      + '</svg>'
    )
  encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
  return "data:image/svg+xml;base64," + encoded


def _classify(products: list[str], text: str) -> dict[str, str]:
  product_text = "; ".join(products)
  searchable = (product_text + " " + text).casefold()
  metal_hits = [description for token, description in IRON_METAL_PATTERNS.items() if token in searchable]
  metal_relation = "No direct iron/metal annotation detected in the antiSMASH region."
  metal_confidence = "not detected"
  if "siderophore" in searchable or "metallophore" in searchable:
    metal_relation = " ".join(dict.fromkeys(metal_hits))
    metal_confidence = "direct BGC-class evidence"
  elif metal_hits:
    metal_relation = " ".join(dict.fromkeys(metal_hits)) + " Candidate association only; inspect the encoded genes before biological interpretation."
    metal_confidence = "gene-annotation candidate"

  normalized_products = {re.sub(r"[^a-z0-9_-]+", "", item.casefold()) for item in products}
  carbon_classes = sorted(item for item in normalized_products if item in CARBON_SKELETON_TYPES or "pks" in item or "nrps" in item or "terpene" in item)
  central_hits = sorted(term for term in CENTRAL_CARBON_TERMS if term in searchable)
  if central_hits:
    carbon_relation = "Candidate link to carbon metabolism through region annotations: " + ", ".join(central_hits) + "."
    carbon_confidence = "gene-annotation candidate"
  elif carbon_classes:
    carbon_relation = "Specialized carbon-skeleton biosynthesis class: " + ", ".join(carbon_classes) + ". This is not, by itself, evidence of central carbon cycling."
    carbon_confidence = "BGC-class chemistry"
  else:
    carbon_relation = "No direct central-carbon annotation or recognized carbon-skeleton BGC class detected."
    carbon_confidence = "not detected"

  references = [LITERATURE["antismash"]]
  if "siderophore" in searchable or "metallophore" in searchable:
    references.append(LITERATURE["siderophore"])
  if any("terpene" in item for item in normalized_products):
    references.append(LITERATURE["terpene"])
  if any("pks" in item for item in normalized_products):
    references.append(LITERATURE["pks"])
  return {
    "iron / metal relevance": metal_relation,
    "metal evidence": metal_confidence,
    "carbon relevance": carbon_relation,
    "carbon evidence": carbon_confidence,
    "literature information": " ".join(dict.fromkeys(references)),
  }


def bgc_metabolism_inventory() -> pd.DataFrame:
  rows: list[dict[str, object]] = []
  for run in discover_antismash_runs():
    run_dir = Path(str(run.get("run_dir", "")))
    if not run_dir.is_dir():
      continue
    region_files = sorted(path for path in run_dir.rglob("*.gbk") if "region" in path.name.casefold())
    for ordinal, region_path in enumerate(region_files, start=1):
      text = region_path.read_text(encoding="utf-8", errors="replace")
      products = _region_products(text)
      cds = _cds_records(text)
      region_number = (_qualifiers((_feature_blocks(text, "region") or [""])[0], "region_number") or [str(ordinal)])[0]
      bgc_name = f"region {region_number}"
      evidence = _classify(products, text)
      if evidence["metal evidence"] == "not detected" and evidence["carbon evidence"] == "not detected":
        continue
      rows.append({
        "MAG": str(run.get("mag_id", "") or run.get("name", "")),
        "BGC": bgc_name,
        "antiSMASH product class": "; ".join(products) if products else "not assigned in region GBK",
        "Cluster figure": _cluster_svg_data_uri(cds, f"{run.get('mag_id', '')} {bgc_name}"),
        **evidence,
        "source region file": region_path.name,
        "source values changed": False,
      })
  columns = [
    "MAG", "BGC", "antiSMASH product class", "Cluster figure",
    "iron / metal relevance", "metal evidence", "carbon relevance",
    "carbon evidence", "literature information", "source region file",
    "source values changed",
  ]
  return pd.DataFrame(rows, columns=columns)


def render_bgc_metabolism_panel(namespace: dict) -> None:
  st = namespace["st"]
  txt = namespace["txt"]
  csv_button = namespace["csv_button"]
  table = bgc_metabolism_inventory()
  st.markdown("##### " + txt(
    "BGCs com relação potencial a ferro/metais e biossíntese de esqueletos de carbono",
    "BGCs potentially related to iron/metals and carbon-skeleton biosynthesis",
  ))
  st.caption(txt(
    "A classificação abaixo é derivada dos arquivos region*.gbk produzidos pelo antiSMASH. Sideróforos/metallóforos constituem evidência direta de classe para quelação de metais; outras palavras-chave são apenas associações candidatas. PKS, NRPS e terpenos indicam biossíntese especializada de esqueletos de carbono e não demonstram, isoladamente, ciclagem central de carbono.",
    "The classification below is derived from the antiSMASH region*.gbk files. Siderophore/metallophore calls are direct class-level evidence for metal chelation; other keywords are candidate associations only. PKS, NRPS and terpene classes indicate specialized carbon-skeleton biosynthesis and do not by themselves demonstrate central carbon cycling.",
  ))
  if table.empty:
    st.info(txt(
      "Nenhum BGC com evidência de ferro/metais ou classe reconhecida de esqueleto de carbono foi encontrado nos arquivos antiSMASH empacotados.",
      "No BGC with iron/metal evidence or a recognized carbon-skeleton class was found in the packaged antiSMASH files.",
    ))
    return
  display = table.drop(columns=["source values changed"]).copy()
  st.dataframe(
    display,
    width="stretch",
    height=min(900, 180 + 82 * len(display)),
    hide_index=True,
    column_config={
      "Cluster figure": st.column_config.ImageColumn(
        txt("Figura do cluster", "Cluster figure"),
        help=txt(
          "Esquema gerado diretamente das coordenadas CDS do arquivo region*.gbk.",
          "Schematic generated directly from CDS coordinates in the region*.gbk file.",
        ),
        width="large",
      ),
    },
  )
  csv_button(
    table.drop(columns=["Cluster figure"]),
    "antiSMASH_BGCs_iron_metals_carbon_evidence.csv",
    txt("Baixar tabela de evidências dos BGCs", "Download BGC evidence table"),
  )
