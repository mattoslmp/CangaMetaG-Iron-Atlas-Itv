from pathlib import Path
import re


def replace_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
  compiled = re.compile(pattern, flags)
  updated, count = compiled.subn(lambda _match: replacement, text, count=1)
  if count != 1:
    raise RuntimeError(f"{label}: replacement count was {count}, expected 1")
  return updated


def patch_app(path: Path) -> None:
  text = path.read_text(encoding="utf-8")

  # Remove internal runtime-state notices from result/presentation modules.
  text = re.sub(
    r'\n  st\.caption\(txt\(\n    "Os resultados ambientais vigentes são preservados.*?\n  \)\)\n',
    '\n', text, count=1, flags=re.S,
  )
  text = re.sub(
    r'\nst\.caption\(txt\(\n  "A navegação agora é persistente:.*?\n\)\)\n',
    '\n', text, count=1, flags=re.S,
  )

  new_overview = r'''  salazar_unique = int(
    markers.loc[
      markers["Study"].astype(str).str.contains("Salazar", case=False, na=False),
      "KO",
    ].astype(str).str.extract(r"(K\d{5})", expand=False).dropna().nunique()
  ) if (not markers.empty and {"Study", "KO"}.issubset(markers.columns)) else 0
  iron_unique = int(
    markers.loc[
      markers["Study"].astype(str).str.contains("New marker", case=False, na=False),
      "KO",
    ].astype(str).str.extract(r"(K\d{5})", expand=False).dropna().nunique()
  ) if (not markers.empty and {"Study", "KO"}.issubset(markers.columns)) else 0

  m1, m2, m3, m4, m5, m6 = st.columns(6)
  m1.metric(txt("Amostras do artigo", "Article samples"), meta["sample.id"].nunique() if "sample.id" in meta.columns else len(meta))
  m2.metric(txt("KOs únicos", "Unique KOs"), markers["KO"].astype(str).str.extract(r"(K\d{5})", expand=False).nunique() if not markers.empty and "KO" in markers.columns else 0)
  m3.metric(txt("KOs derivados de Salazar", "Salazar-derived KOs"), salazar_unique)
  m4.metric(txt("KOs associados ao ferro", "Iron-associated KOs"), iron_unique)
  m5.metric(txt("Ambientes IMG/M", "IMG/M environments"), iron_meta["sample_id"].nunique() if not iron_meta.empty and "sample_id" in iron_meta.columns else len(iron_meta))
  m6.metric(txt("MAGs", "MAGs"), len(load_sheet("table7", "bins-identificados")))

  c1, c2 = st.columns([0.52, 0.48])
  with c1:
    st.markdown("#### " + txt("Atualização dos biomarcadores e rastreabilidade", "Biomarker update and traceability"))
    st.markdown(txt(
      f"**Salazar et al. (2019)** forneceram a estrutura de referência para genes marcadores de ciclos biogeoquímicos usada neste atlas. O conjunto empacotado contém **{salazar_unique} KOs biogeoquímicos únicos derivados dessa referência**. A publicação atual **atualiza e amplia** esse quadro, consolidando um painel de **195 biomarcadores biogeoquímicos**, dos quais **171 foram detectados** nas amostras do estudo, e acrescentando um painel dedicado de **132 biomarcadores associados ao ferro**. Na versão empacotada do atlas, **{iron_unique} KOs únicos** estão representados explicitamente na matriz focada em ferro/metais. Dessa forma, o estudo não apenas reutiliza a referência de Salazar: ele a expande para sedimentos tropicais ferruginosos e mantém a proveniência de cada marcador.",
      f"**Salazar et al. (2019)** provided the reference framework for biogeochemical-cycle marker genes used in this atlas. The packaged dataset contains **{salazar_unique} unique biogeochemical KOs derived from that reference**. The present publication **updates and expands** the framework by consolidating a panel of **195 biogeochemical biomarkers**, of which **171 were detected** in the study samples, and by adding a dedicated panel of **132 iron-associated biomarkers**. In the packaged atlas release, **{iron_unique} unique KOs** are represented explicitly in the iron/metals-focused matrix. The study therefore does not merely reuse the Salazar reference; it extends it to tropical ferruginous sediments while preserving marker-level provenance."
    ))
    st.caption(txt(
      f"Referências rastreadas: {SALAZAR_CITATION} Publicação atual: {ARTICLE_CITATION}",
      f"Traced references: {SALAZAR_CITATION} Current publication: {ARTICLE_CITATION}"
    ))
    st.markdown(txt(
      "**IMG/M source:** os metadados dos ambientes ricos em ferro vêm da aba `Iron-rich-environment` da Supplementary Table 8, derivada do portal Integrated Microbial Genomes with Microbiome Samples mantido pelo JGI.",
      "**IMG/M source:** metadata for iron-rich environments come from the `Iron-rich-environment` sheet in Supplementary Table 8, derived from the Integrated Microbial Genomes with Microbiome Samples portal maintained by JGI."
    ))
    if available_gbk_count() == 0:
      st.warning(txt(
        "Os FASTA foram incluídos, mas nenhum GBK/GBFF foi encontrado.",
        "FASTA files are included, but no GBK/GBFF files were found."
      ))
  with c2:
    st.markdown("#### " + txt("Amostras, sazonalidade e novidade do estudo", "Study samples, seasonality and novelty"))
    total_samples = int(meta["sample.id"].nunique()) if "sample.id" in meta.columns else len(meta)
    n_lakes = int(meta["lake"].dropna().astype(str).nunique()) if "lake" in meta.columns else 0
    n_dry = int((meta["season"].astype(str).str.lower() == "dry").sum()) if "season" in meta.columns else 0
    n_rainy = int((meta["season"].astype(str).str.lower() == "rainy").sum()) if "season" in meta.columns else 0
    lake_names = ", ".join(sorted(meta["lake"].dropna().astype(str).unique())) if "lake" in meta.columns else ""
    st.markdown(txt(
      f"O estudo inclui **{total_samples} amostras de sedimento** provenientes de **{n_lakes} lagoas lateríticas amazônicas** — **{lake_names}** — com coletas nos períodos **seco e chuvoso**. A novidade do atlas é integrar, para essas mesmas amostras, metadados de coleta e estação, perfis taxonômicos, biomarcadores KO dos ciclos biogeoquímicos, biomarcadores associados ao ferro, módulos KEGG/KEMET, MAGs e comparações com outros ambientes ricos em ferro. A tabela detalhada abaixo mantém explicitamente a **estação do ano de cada amostra**.",
      f"The study includes **{total_samples} sediment samples** from **{n_lakes} Amazonian lateritic lakes** — **{lake_names}** — collected during **dry and rainy seasons**. The novelty of the atlas is the integration, for these same samples, of collection and seasonal metadata, taxonomic profiles, biogeochemical-cycle KO biomarkers, iron-associated biomarkers, KEGG/KEMET modules, MAGs and comparisons with other iron-rich environments. The detailed table below explicitly retains the **season assigned to every sample**."
    ))
    if not meta.empty and {"sample.id", "lake", "season"}.issubset(meta.columns):
      sample_summary = (
        meta[["sample.id", "lake", "season"]]
        .drop_duplicates()
        .assign(
          dry=lambda frame: (frame["season"].astype(str).str.lower() == "dry").astype(int),
          rainy=lambda frame: (frame["season"].astype(str).str.lower() == "rainy").astype(int),
        )
        .groupby("lake", as_index=False)
        .agg(samples=("sample.id", "nunique"), dry_samples=("dry", "sum"), rainy_samples=("rainy", "sum"))
      )
      show_table(sample_summary, "metadata_lake_season_summary", height=190)
    st.caption(txt(
      f"Distribuição sazonal: **{n_dry} amostras do período seco** e **{n_rainy} amostras do período chuvoso**.",
      f"Seasonal distribution: **{n_dry} dry-season samples** and **{n_rainy} rainy-season samples**."
    ))
    cols = [c for c in ["sample.id", "collection_date", "lake", "season", "lat", "lon", "environment_feature"] if c in meta.columns]
    show_table(meta[cols], "metadata_preview", height=320)
    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))
'''

  text = replace_once(
    text,
    r'  m1, m2, m3, m4, m5, m6 = st\.columns\(6\)\n.*?\n  if st\.session_state\.get\("admin_authenticated", False\):',
    new_overview + '\n  if st.session_state.get("admin_authenticated", False):',
    'overview block',
    flags=re.S,
  )

  text = replace_once(
    text,
    r'  st\.caption\(txt\(\n    "Coloque cada diretório antiSMASH já descompactado.*?MAG\.<number>\."\n  \)\)\n',
    '',
    'antiSMASH presentation caption',
    flags=re.S,
  )

  anchor = '    st.code("python -m pip install -r requirements.txt\\nstreamlit run app.py", language="bash")\n'
  insert = anchor + '''    st.markdown("### " + txt("Preparação dos diretórios antiSMASH", "antiSMASH directory preparation"))
    st.info(txt(
      "Coloque cada diretório antiSMASH já descompactado em `data/kegg_modules/mags/gbk_antismash/`. Os nomes podem conter `strict`, `orig`, `permissive`, `metawrap`, `repaired`, contadores de reparo ou marcadores como `(1)`; durante a leitura, o app normaliza esses nomes para `MAG.<número>`.",
      "Place each extracted antiSMASH directory under `data/kegg_modules/mags/gbk_antismash/`. Names may contain `strict`, `orig`, `permissive`, `metawrap`, `repaired`, repair counters or markers such as `(1)`; during loading, the app normalizes these names to `MAG.<number>`."
    ))
'''
  if anchor not in text:
    raise RuntimeError('Methods/execution insertion anchor not found')
  text = text.replace(anchor, insert, 1)
  path.write_text(text, encoding='utf-8')


def patch_workflow(path: Path) -> None:
  text = path.read_text(encoding='utf-8')
  text = text.replace(
    '  title_x = x + 0.04 if number is not None else x + w / 2\n',
    '  title_x = x + 0.062 if number is not None else x + w / 2\n',
  )
  text = text.replace(
    "    cx = x + 0.025\n    cy = y + h - 0.030\n    ax.add_patch(Circle((cx, cy), 0.017, facecolor=edge, edgecolor='none', zorder=4))\n",
    "    cx = x + 0.027\n    cy = y + h - 0.030\n    ax.add_patch(Circle((cx, cy), 0.014, facecolor=edge, edgecolor='none', zorder=4))\n",
  )
  path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
  patch_app(Path('app.py'))
  patch_workflow(Path('scripts/generate_atlas_workflow_figure.py'))
