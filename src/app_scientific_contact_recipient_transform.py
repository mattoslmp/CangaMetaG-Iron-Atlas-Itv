from __future__ import annotations


RECIPIENT = "gilopesnunes@gmail.com"
RECIPIENT_NAME = "Gisele Lopes Nunes"


# The public scientific-collaboration form has one fixed recipient. Ignore any
# legacy multi-recipient value persisted in the settings file.
recipient_start = source.find("def contact_recipients_from_settings() -> list[str]:\n")
recipient_end = source.find("\ndef save_contact_submission", recipient_start)
if recipient_start < 0 or recipient_end < 0:
  raise RuntimeError("Could not locate the scientific-contact recipient function")
recipient_function = f'''SCIENTIFIC_COLLABORATION_RECIPIENT = "{RECIPIENT}"
SCIENTIFIC_COLLABORATION_RECIPIENT_NAME = "{RECIPIENT_NAME}"


def contact_recipients_from_settings() -> list[str]:
  return [SCIENTIFIC_COLLABORATION_RECIPIENT]

'''
source = source[:recipient_start] + recipient_function + source[recipient_end + 1:]


# Prefer an already-configured SMTP server when available. Otherwise submit to
# FormSubmit's AJAX endpoint. On the first submission FormSubmit sends a single
# activation e-mail to Gisele; after she confirms it, retained and future
# submissions are forwarded automatically without SMTP or Streamlit setup.
sender_start = source.find("def try_send_contact_email(payload: dict, recipients: list[str]) -> tuple[bool, str]:\n")
sender_end = source.find("\ndef contact_form_panel", sender_start)
if sender_start < 0 or sender_end < 0:
  raise RuntimeError("Could not locate the scientific-contact sender function")
sender_function = '''def try_send_contact_email(payload: dict, recipients: list[str]) -> tuple[bool, str]:
  recipient = SCIENTIFIC_COLLABORATION_RECIPIENT
  subject_prefix = str(load_app_settings().get(
    "contact_subject_prefix",
    "Amazonian Lateritic Lakes Metagenomic Atlas collaboration contact",
  ))
  subject = f"{subject_prefix}: {payload.get('name', 'Visitor')}"

  smtp_host = runtime_setting("SMTP_HOST", "")
  smtp_port = int(runtime_setting("SMTP_PORT", "587") or 587)
  smtp_user = runtime_setting("SMTP_USER", "")
  smtp_password = runtime_setting("SMTP_PASSWORD", "")
  smtp_from = runtime_setting("SMTP_FROM", smtp_user or "")
  if smtp_host and smtp_from:
    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = recipient
    msg["Subject"] = subject
    reply_to = str(payload.get("email", "")).strip()
    if reply_to:
      msg["Reply-To"] = reply_to
    msg.set_content(
      "New contact message from the Amazonian Lateritic Lakes Metagenomic Atlas.\n\n"
      f"Name: {payload.get('name', '')}\n"
      f"Email: {payload.get('email', '')}\n"
      f"Affiliation: {payload.get('affiliation', '')}\n"
      f"Interest: {payload.get('interest', '')}\n"
      f"Message:\n{payload.get('message', '')}\n\n"
      f"Timestamp UTC/local app: {payload.get('timestamp', '')}\n"
      f"Program: {PUBLIC_PROGRAM_NAME} v{PUBLIC_PROGRAM_VERSION} ({DATABASE_RELEASE_LABEL})\n"
    )
    try:
      with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.starttls()
        if smtp_user and smtp_password:
          server.login(smtp_user, smtp_password)
        server.send_message(msg)
      return True, txt(
        "Mensagem enviada diretamente para Gisele Lopes Nunes.",
        "Message sent directly to Gisele Lopes Nunes.",
      )
    except Exception as exc:
      LOGGER.warning("SMTP contact delivery failed; trying FormSubmit: %s", exc)

  visitor_email = str(payload.get("email", "")).strip()
  form_data = {
    "name": str(payload.get("name", "")).strip(),
    "email": visitor_email,
    "_replyto": visitor_email,
    "affiliation": str(payload.get("affiliation", "")).strip(),
    "interest": str(payload.get("interest", "")).strip(),
    "message": str(payload.get("message", "")).strip(),
    "timestamp": str(payload.get("timestamp", "")).strip(),
    "program": f"{PUBLIC_PROGRAM_NAME} v{PUBLIC_PROGRAM_VERSION} ({DATABASE_RELEASE_LABEL})",
    "_subject": subject,
    "_template": "table",
    "_honey": "",
  }
  try:
    response = requests.post(
      f"https://formsubmit.co/ajax/{recipient}",
      json=form_data,
      headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "CangaMetaG-Iron-Atlas/1.0",
      },
      timeout=25,
    )
    try:
      response_data = response.json()
    except Exception:
      response_data = {}
    remote_message = str(response_data.get("message", "")).strip()
    raw_success = response_data.get("success", True)
    if isinstance(raw_success, str):
      remote_success = raw_success.strip().casefold() not in {"false", "0", "no", "error"}
    else:
      remote_success = bool(raw_success)
    success = bool(response.ok and remote_success)
    if success:
      activation_pending = bool(re.search(
        r"activat|confirm|verify|verification",
        remote_message,
        flags=re.IGNORECASE,
      ))
      if activation_pending:
        return True, txt(
          "A mensagem foi registrada. O Gmail de Gisele receberá o e-mail de ativação; ela precisa apenas clicar no link uma única vez. Após a confirmação, esta mensagem e as próximas serão entregues automaticamente.",
          "The message was recorded. Gisele's Gmail account will receive the activation e-mail; she only needs to click the link once. After confirmation, this and future messages will be delivered automatically.",
        )
      return True, txt(
        "Mensagem registrada para Gisele Lopes Nunes. Se esta for a primeira utilização do formulário, ela receberá no Gmail um link de ativação e precisará apenas clicar nele uma única vez; depois, as mensagens serão entregues automaticamente.",
        "Message registered for Gisele Lopes Nunes. If this is the form's first use, she will receive a Gmail activation link and only needs to click it once; messages will then be delivered automatically.",
      )
    detail = remote_message or f"HTTP {response.status_code}"
    return False, txt(
      "O encaminhamento automático não respondeu corretamente: " + detail,
      "Automatic forwarding did not respond correctly: " + detail,
    )
  except Exception as exc:
    return False, txt(
      "O encaminhamento automático falhou: " + str(exc) + ". A mensagem foi salva localmente e o botão de e-mail manual permanece disponível.",
      "Automatic forwarding failed: " + str(exc) + ". The message was saved locally and the manual e-mail button remains available.",
    )

'''
source = source[:sender_start] + sender_function + source[sender_end + 1:]


# Show the delivery result returned by SMTP/FormSubmit instead of a generic
# success sentence, so first-use activation is clearly communicated.
source = source.replace(
  '''        if sent:
          st.success(txt("Mensagem enviada com sucesso para os responsáveis pelo projeto.", "Message sent successfully to the project contacts."))
''',
  '''        if sent:
          st.success(info)
''',
  1,
)


# Keep the administrative panel aligned with the fixed Gmail recipient. The
# subject prefix remains editable, but no additional address or SMTP setup is
# required from Gisele.
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
      "As mensagens são encaminhadas exclusivamente para Gisele Lopes Nunes. Na primeira submissão, o Gmail recebe um e-mail de ativação do FormSubmit; Gisele precisa apenas clicar no link uma única vez, sem configurar SMTP, senha ou Streamlit.",
      "Messages are forwarded exclusively to Gisele Lopes Nunes. On the first submission, Gmail receives a FormSubmit activation e-mail; Gisele only needs to click the link once, without configuring SMTP, a password or Streamlit.",
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
          "Configuração salva. Gisele Lopes Nunes permanece como única destinatária.",
          "Configuration saved. Gisele Lopes Nunes remains the only recipient.",
        ))

'''
source = source[:admin_start] + admin_panel + source[admin_end + 1:]


# Public wording must also reflect the single fixed recipient.
source = source.replace(
  '"Destinatários configurados pelo admin: " + "; ".join(recipients),\n       "Admin-configured recipients: " + "; ".join(recipients)',
  '"Destinatária: Gisele Lopes Nunes <" + "; ".join(recipients) + ">",\n       "Recipient: Gisele Lopes Nunes <" + "; ".join(recipients) + ">"',
  1,
)
