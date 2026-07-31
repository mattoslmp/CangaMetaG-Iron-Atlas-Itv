from __future__ import annotations

"""Keep public figure method labels concise while preserving statistical results."""


MARKER = "CANGAMETAG_CONCISE_SCIENTIFIC_METHOD_TEXT_V1 = 1"

if MARKER not in source:
  source = source.replace(
    '"Método: proporções relativas dos gêneros transformadas pela raiz quadrada, seguidas de distância Bray–Curtis. PERMANOVA com 999 permutações testou diferenças entre lagoas, estações e combinações lagoa–estação; PERMDISP/betadisper testou homogeneidade da dispersão. " + inference_summary(beta_tests),',
    '"Métodos: PERMANOVA e PERMDISP. " + inference_summary(beta_tests),',
  )
  source = source.replace(
    '"Method: square-root-transformed genus relative proportions followed by Bray-Curtis distances. PERMANOVA with 999 permutations tested differences among lakes, seasons and lake–season combinations; PERMDISP/betadisper tested homogeneity of dispersion. " + inference_summary(beta_tests),',
    '"Methods: PERMANOVA and PERMDISP. " + inference_summary(beta_tests),',
  )
  source = source.replace(
    'f"Método: composição de gêneros transformada por Hellinger e restringida pelas variáveis ambientais padronizadas; significância avaliada por 999 permutações para o modelo global e para cada eixo. Resultado: R²={r2:.3g}, R² ajustado={adjusted_r2:.3g}, pseudo-F={pseudo_f:.3g}, p global={pvalue:.3g}, p RDA1={axis1_p:.3g}, p RDA2={axis2_p:.3g}; modelo global {result_pt} a 5%.",',
    'f"Método: RDA com teste de permutação. R²={r2:.3g}, R² ajustado={adjusted_r2:.3g}, pseudo-F={pseudo_f:.3g}, p global={pvalue:.3g}, p RDA1={axis1_p:.3g}, p RDA2={axis2_p:.3g}; modelo global {result_pt} a 5%.",',
  )
  source = source.replace(
    'f"Method: Hellinger-transformed genus composition constrained by standardized environmental variables; significance evaluated with 999 permutations for the global model and each axis. Result: R²={r2:.3g}, adjusted R²={adjusted_r2:.3g}, pseudo-F={pseudo_f:.3g}, global p={pvalue:.3g}, RDA1 p={axis1_p:.3g}, RDA2 p={axis2_p:.3g}; global model {result_en} at 5%.",',
    'f"Method: RDA with permutation test. R²={r2:.3g}, adjusted R²={adjusted_r2:.3g}, pseudo-F={pseudo_f:.3g}, global p={pvalue:.3g}, RDA1 p={axis1_p:.3g}, RDA2 p={axis2_p:.3g}; global model {result_en} at 5%.",',
  )

  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
def _concise_scientific_method_name(value: object) -> str:
  text = str(value or "").strip()
  lowered = text.casefold()
  if not text:
    return "—"
  if "permanova" in lowered or "permdisp" in lowered:
    return "PERMANOVA; PERMDISP; RDA"
  if "mann" in lowered or "kruskal" in lowered or "welch" in lowered or "anova" in lowered:
    return "one-way ANOVA; Kruskal-Wallis; Welch t-test; Mann-Whitney U; Benjamini-Hochberg FDR"
  if "deseq2" in lowered:
    return "DESeq2"
  if "aldex2" in lowered:
    return "ALDEx2"
  if "raref" in lowered or "alpha" in lowered:
    return "Deterministic rarefaction; alpha-diversity metrics"
  if "bray" in lowered or "nmds" in lowered or "pcoa" in lowered:
    return "Bray-Curtis NMDS/PCoA"
  first = text.split(".", 1)[0].split(";", 1)[0].strip()
  return first[:180] if first else text[:180]


if "_scientific_script_metadata" in globals():
  def _scientific_script_metadata(
    *,
    method: str,
    script: str,
    command: str,
    inputs: list[str],
    outputs: list[str],
  ) -> pd.DataFrame:
    return pd.DataFrame([
      {"Field": "Method", "Value": _concise_scientific_method_name(method)},
      {"Field": "Script", "Value": script or "—"},
      {"Field": "Command", "Value": command or "—"},
      {"Field": "Input", "Value": "; ".join(inputs) if inputs else "—"},
      {"Field": "Output", "Value": "; ".join(outputs) if outputs else "—"},
    ])
'''
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)

  source += f"\n\n{MARKER}\n"
