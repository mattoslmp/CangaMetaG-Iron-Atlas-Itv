from __future__ import annotations


RECIPIENT = "Gisele.Nunes@itv.org"


# The public scientific-collaboration form has one institutional recipient.
# Ignore any legacy multi-recipient value persisted in the settings file.
recipient_start = source.find("def contact_recipients_from_settings() -> list[str]:\n")
recipient_end = source.find("\ndef save_contact_submission", recipient_start)
if recipient_start < 0 or recipient_end < 0:
  raise RuntimeError("Could not locate the scientific-contact recipient function")
recipient_function = f'''SCIENTIFIC_COLLABORATION_RECIPIENT = "{RECIPIENT}"


def contact_recipients_from_settings() -> list[str]:
  return [SCIENTIFIC_COLLABORATION_RECIPIENT]

'''
source = source[:recipient_start] + recipient_function + source[recipient_end + 1:]


# Keep the administrative panel aligned with the fixed recipient. The subject
# prefix remains editable, but no additional destination address can be added.
admin_start = source.find("def admin_contact_settings_panel() -> None:\n")
admin_end = source.find("\ndef code_reproducibility_tab", admin_start)
if admin_start < 0 or admin_end < 0:
  raise RuntimeError("Could not locate the scientific-contact settings panel")
admin_panel = '''def admin_contact_settings_panel() -> None:
  settings = load_app_settings()
  with st.expander(
    txt("Contato público — destinatária", "Public contact — recipient"),
    expanded=False,
  ):
    st.caption(txt(
      "As mensagens de colaboração científica são encaminhadas exclusivamente para Gisele Nunes.",
      "Scientific-collaboration messages are sent exclusively to Gisele Nunes.",
    ))
    st.text_input(
      txt("E-mail de destino", "Destination e-mail"),
      value=SCIENTIFIC_COLLABORATION_RECIPIENT,
      disabled=True,
      key="admin_contact_recipient_fixed",
    )
    subject_prefix = st.text_input(
      txt("Prefixo do assunto", "Subject prefix"),
      value=str(settings.get(
        "contact_subject_prefix",
        "Amazonian Lateritic Lakes Metagenomic Atlas collaboration contact",
      )),
      key="admin_contact_subject_prefix",
    )
    if st.button(
      txt("Salvar configuração de contato", "Save contact configuration"),
      key="save_contact_recipients",
      type="primary",
      width="stretch",
    ):
      settings["contact_recipients"] = SCIENTIFIC_COLLABORATION_RECIPIENT
      settings["contact_subject_prefix"] = subject_prefix.strip()
      settings["contact_settings_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
      if save_app_settings(settings):
        st.success(txt(
          "Configuração salva. Gisele Nunes permanece como única destinatária.",
          "Configuration saved. Gisele Nunes remains the only recipient.",
        ))

'''
source = source[:admin_start] + admin_panel + source[admin_end + 1:]


# Public wording must also reflect the single fixed recipient.
source = source.replace(
  '"Destinatários configurados pelo admin: " + "; ".join(recipients),\n       "Admin-configured recipients: " + "; ".join(recipients)',
  '"Destinatária: " + "; ".join(recipients),\n       "Recipient: " + "; ".join(recipients)',
  1,
)
source = source.replace(
  '"Mensagem enviada com sucesso para os responsáveis pelo projeto.", "Message sent successfully to the project contacts."',
  '"Mensagem enviada com sucesso para Gisele Nunes.", "Message sent successfully to Gisele Nunes."',
  1,
)
