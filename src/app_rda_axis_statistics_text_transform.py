from __future__ import annotations

MARKER = "CANGAMETAG_RDA_AXIS_STATISTICS_TEXT_V1 = 1"

if MARKER not in source:
  old = '''        r2 = pd.to_numeric(pd.Series([row.get("R2")]), errors="coerce").iloc[0]
        pseudo_f = pd.to_numeric(pd.Series([row.get("pseudo_F")]), errors="coerce").iloc[0]
        pvalue = pd.to_numeric(pd.Series([row.get("pvalue_permutation")]), errors="coerce").iloc[0]
        result_pt = "significativo" if pd.notna(pvalue) and pvalue < 0.05 else "não significativo"
        result_en = "significant" if pd.notna(pvalue) and pvalue < 0.05 else "not significant"
        st.markdown(txt(
          f"Método: composição de gêneros transformada por Hellinger e restringida pelas variáveis ambientais padronizadas; teste global por permutação. Resultado: R²={r2:.3g}, pseudo-F={pseudo_f:.3g}, p={pvalue:.3g}; modelo {result_pt} a 5%.",
          f"Method: Hellinger-transformed genus composition constrained by standardized environmental variables; global permutation test. Result: R²={r2:.3g}, pseudo-F={pseudo_f:.3g}, p={pvalue:.3g}; model {result_en} at 5%.",
        ))'''
  new = '''        r2 = pd.to_numeric(pd.Series([row.get("R2")]), errors="coerce").iloc[0]
        adjusted_r2 = pd.to_numeric(pd.Series([row.get("adjusted_R2")]), errors="coerce").iloc[0]
        pseudo_f = pd.to_numeric(pd.Series([row.get("pseudo_F")]), errors="coerce").iloc[0]
        pvalue = pd.to_numeric(pd.Series([row.get("pvalue_permutation")]), errors="coerce").iloc[0]
        axis1_p = pd.to_numeric(pd.Series([row.get("RDA1_axis_permutation_p")]), errors="coerce").iloc[0]
        axis2_p = pd.to_numeric(pd.Series([row.get("RDA2_axis_permutation_p")]), errors="coerce").iloc[0]
        result_pt = "significativo" if pd.notna(pvalue) and pvalue < 0.05 else "não significativo"
        result_en = "significant" if pd.notna(pvalue) and pvalue < 0.05 else "not significant"
        st.markdown(txt(
          f"Método: composição de gêneros transformada por Hellinger e restringida pelas variáveis ambientais padronizadas; significância avaliada por 999 permutações para o modelo global e para cada eixo. Resultado: R²={r2:.3g}, R² ajustado={adjusted_r2:.3g}, pseudo-F={pseudo_f:.3g}, p global={pvalue:.3g}, p RDA1={axis1_p:.3g}, p RDA2={axis2_p:.3g}; modelo global {result_pt} a 5%.",
          f"Method: Hellinger-transformed genus composition constrained by standardized environmental variables; significance evaluated with 999 permutations for the global model and each axis. Result: R²={r2:.3g}, adjusted R²={adjusted_r2:.3g}, pseudo-F={pseudo_f:.3g}, global p={pvalue:.3g}, RDA1 p={axis1_p:.3g}, RDA2 p={axis2_p:.3g}; global model {result_en} at 5%.",
        ))'''
  source = source.replace(old, new, 1)
  source += f"\n\n{MARKER}\n"
