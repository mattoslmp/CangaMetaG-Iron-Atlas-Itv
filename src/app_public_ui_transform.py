from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Keep data-integrity rules in the implementation without presenting internal
# processing notes as scientific results in the public interface.
source = source.replace(
  '  st.info("Data provenance: no synthetic, simulated or randomly generated values are used. MAG and lagoon-metagenome panels read their original packaged KEMET status matrices. ST8 external and combined panels use categorical module-status matrices deterministically derived from the KO profiles in tables/Supplementary_Table_8.xlsx; no imputation or value replacement is applied.")\n',
  '',
  1,
)
source = source.replace(
  '''  st.info(txt(
    "A figura local de componentes do módulo não substitui o diagrama oficial do KEGG. Ela colore os KOs detectados em verde e os KOs ausentes/alternativos em vermelho, mantendo um link para a entrada oficial do módulo no KEGG.",
    "The local module-component figure does not replace the official KEGG diagram. It colors detected KOs green and missing/alternative KOs red while retaining a link to the official KEGG module entry."
  ))
''',
  '',
  1,
)


# Make the BV-BRC synchronization and already-downloaded results available from
# the public MAG page. The backend still uses argument-list subprocess calls,
# confines writes to the project Annotation directory and never accepts a
# password through the Streamlit interface.
admin_gate = '''  if not is_admin_authenticated():
    render_admin_only_download_notice("Sincronização BV-BRC CLI")
    st.caption(txt(
      "As anotações já baixadas em `Annotation/MAGx/` permanecem disponíveis para visualização. O app nunca executa `p3-cp` para usuários públicos.",
      "Annotations already downloaded into `Annotation/MAGx/` remain available for viewing. The app never runs `p3-cp` for public users.",
    ))
    return
  st.markdown("#### " + txt("Sincronização automática BV-BRC CLI — admin", "Automatic BV-BRC CLI synchronization — admin"))
'''
public_gate = '''  st.markdown("#### " + txt("Sincronização de anotações BV-BRC", "BV-BRC annotation synchronization"))
  st.caption(txt(
    "As anotações já presentes em `Annotation/MAGx/` ficam disponíveis imediatamente. Quando o servidor possui o BV-BRC CLI instalado e uma sessão previamente autenticada, os controles abaixo também podem recuperar resultados ausentes sem solicitar senha na aplicação.",
    "Annotations already present under `Annotation/MAGx/` are immediately available. When the server has the BV-BRC CLI installed and a previously authenticated session, the controls below can also retrieve missing results without requesting a password in the application.",
  ))
'''
source = replace_once(source, admin_gate, public_gate, "public BV-BRC synchronization panel")

source = source.replace(
  '''    st.markdown(txt(
      "Este painel usa `p3-ls` e `p3-cp` do BV-BRC CLI para baixar os resultados do Workspace diretamente para `Annotation/MAG2`, `Annotation/MAG3`, etc. Por padrão, o app **primeiro verifica a pasta local e NÃO baixa novamente** se já encontrar arquivos válidos para o MAG. O app **não armazena sua senha**; faça o login uma vez no terminal com `p3-login mattoslmp` e depois use os botões abaixo.",
      "This panel uses BV-BRC CLI `p3-ls` and `p3-cp` to download Workspace results directly into `Annotation/MAG2`, `Annotation/MAG3`, etc. By default, the app **checks the local folder first and does NOT download again** when valid MAG files already exist. The app **does not store your password**; log in once in the terminal with `p3-login mattoslmp`, then use the buttons below."
    ))
    st.code("p3-login mattoslmp", language="bash")
''',
  '''    st.markdown(txt(
      "O painel verifica primeiro `Annotation/MAGx/` e reutiliza os arquivos já existentes. Quando um MAG estiver ausente e o servidor tiver uma sessão BV-BRC CLI válida, `p3-ls` e `p3-cp` recuperam somente os resultados necessários do Workspace configurado.",
      "The panel checks `Annotation/MAGx/` first and reuses existing files. When a MAG is missing and the server has a valid BV-BRC CLI session, `p3-ls` and `p3-cp` retrieve only the required results from the configured Workspace."
    ))
''',
  1,
)

source = source.replace(
  '    elif is_admin_authenticated() and not folder and bool(st.session_state.get("bvbrc_auto_sync_selected", False)):\n',
  '    elif not folder and bool(st.session_state.get("bvbrc_auto_sync_selected", False)):\n',
  1,
)


# The main article map now uses the exact same coordinate dataset as the
# Taxonomic profiles page before adding the external ST8 environments.
source = source.replace(
  '  lake_map_meta = meta.copy()\n',
  '  lake_map_meta = taxonomy_samples_metadata()\n',
  1,
)


# Preserve the publication Figure 1 because its complete cartographic design
# cannot be reproduced exactly by a web tile map. Add a companion interactive
# view driven by the same article sample coordinates used in Taxonomic profiles.
study_static_block = '''  figure1_sampling_path = BASE_DIR / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  st.markdown("### " + txt("Área de estudo e desenho amostral", "Study area and sampling design"))
  if figure1_sampling_path.exists():
    st.image(str(figure1_sampling_path), width="stretch")
    st.caption(txt(
      "Área de estudo e desenho amostral. Localização das lagoas lateríticas amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período seco e 10 do período chuvoso.",
      "Study area and sampling design. Location of the Amazonian lateritic lakes Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes 20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples."
    ))
  else:
    st.warning(txt(
      "A Figura 1 do mapa amostral não foi encontrada no diretório canônico de figuras finais.",
      "Figure 1 sampling map was not found in the canonical final-figures directory."
    ))
'''
study_interactive_block = study_static_block + """
  interactive_study_meta = taxonomy_samples_metadata()
  if not interactive_study_meta.empty and {"lat", "lon"}.issubset(interactive_study_meta.columns):
    interactive_study_meta = apply_amazonian_lake_coordinate_overrides(interactive_study_meta)
    st.markdown(
      f'''<div style="margin:.8rem 0 .55rem 0;padding:.88rem 1rem;border-radius:16px;
      background:#EAF7F4;border:2px solid #0F766E;color:#064E3B;font-weight:850;
      font-size:1.08rem;">🗺️ {txt('Mapa interativo dos pontos de amostragem', 'Interactive sampling-point map')}</div>''',
      unsafe_allow_html=True,
    )
    with st.expander(
      txt(
        "Explorar as coordenadas das lagoas e amostras",
        "Explore lake and sample coordinates",
      ),
      expanded=True,
    ):
      show_leaflet_satellite_map(
        interactive_study_meta,
        key="overview_exact_taxonomy_sampling_coordinates_v1",
        title=txt(
          "Pontos de amostragem das lagoas lateríticas de Carajás",
          "Sampling points of the Carajás lateritic lakes",
        ),
        height=760,
      )
      interactive_cols = [column for column in [
        "sample.id", "matrix_column", "lake", "season", "sampling_position",
        "site", "lat", "lon", "IMG_JGI_analysis_project_id",
        "IMG_JGI_taxon_oid", "ENA_study_accession",
      ] if column in interactive_study_meta.columns]
      show_table(
        interactive_study_meta[interactive_cols].drop_duplicates(),
        "overview_exact_sampling_coordinate_table_v1",
        height=420,
      )
"""
source = replace_once(source, study_static_block, study_interactive_block, "interactive study-area map")


# Increase body, control, caption, tab and navigation typography throughout the
# application while preserving the existing visual hierarchy.
font_css = '''
st.markdown(
  """
  <style>
    html, body, [data-testid="stAppViewContainer"] {
      font-size: 17px;
    }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li {
      font-size: 1.04rem !important;
      line-height: 1.62 !important;
    }
    [data-testid="stCaptionContainer"],
    .stCaption {
      font-size: 0.96rem !important;
      line-height: 1.48 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] input,
    [data-testid="stSidebarNav"] span {
      font-size: 1.02rem !important;
      line-height: 1.42 !important;
    }
    [data-baseweb="tab"] {
      font-size: 1.02rem !important;
      font-weight: 700 !important;
    }
    .stButton button,
    .stDownloadButton button,
    .stLinkButton a,
    [data-baseweb="select"] *,
    [data-baseweb="input"] input,
    textarea {
      font-size: 1rem !important;
    }
    h1 { font-size: 2.45rem !important; }
    h2 { font-size: 1.95rem !important; }
    h3 { font-size: 1.58rem !important; }
    h4 { font-size: 1.32rem !important; }
  </style>
  """,
  unsafe_allow_html=True,
)
'''
source = replace_once(source, 'page_header()\n', font_css + 'page_header()\n', "global typography")
