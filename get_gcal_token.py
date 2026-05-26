"""
get_gcal_token.py — Gera o refresh_token do Google Calendar (rode UMA VEZ localmente).

USO:
  1. No Google Cloud Console → Credenciais → seu OAuth2 Client ID:
     - Adicione  http://localhost:8080  em "URIs de redirecionamento autorizados"
     - Baixe o JSON de credenciais (ou use client_id e client_secret manualmente abaixo)

  2. Preencha CLIENT_ID e CLIENT_SECRET aqui embaixo (ou crie um .env com elas)

  3. Execute:  python get_gcal_token.py
     → Abrirá o navegador para você autorizar o acesso ao Google Calendar
     → Imprime no terminal o refresh_token

  4. Adicione nos Secrets do Streamlit Cloud:
       GOOGLE_CLIENT_ID     = "...apps.googleusercontent.com"
       GOOGLE_CLIENT_SECRET = "GOCSPX-..."
       GOOGLE_REFRESH_TOKEN = "1//..."
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

# ── Preencha ou carregue do .env ──────────────────────────────────────────────
CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env ou neste arquivo.")
    raise SystemExit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

client_config = {
    "installed": {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

print("\n" + "=" * 60)
print("✅ Autorização concluída! Adicione nos Secrets do Streamlit:")
print("=" * 60)
print(f"GOOGLE_CLIENT_ID     = \"{CLIENT_ID}\"")
print(f"GOOGLE_CLIENT_SECRET = \"{CLIENT_SECRET}\"")
print(f"GOOGLE_REFRESH_TOKEN = \"{creds.refresh_token}\"")
print("=" * 60 + "\n")
