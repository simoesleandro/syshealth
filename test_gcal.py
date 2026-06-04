"""Testa Google Calendar com credenciais do .env (rode após atualizar GOOGLE_REFRESH_TOKEN)."""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

_BR = ZoneInfo("America/Sao_Paulo")


def main():
    for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"):
        if not (os.getenv(key) or "").strip():
            print(f"Falta {key} no .env")
            return 1

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    print("Renovando access token…")
    creds.refresh(Request())
    print("OK — token renovado")

    hoje = datetime.now(_BR).strftime("%Y-%m-%d")
    fim_utc = (date.fromisoformat(hoje) + timedelta(days=1)).isoformat() + "T02:59:59Z"
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    result = service.events().list(
        calendarId="primary",
        timeMin=f"{hoje}T03:00:00Z",
        timeMax=fim_utc,
        singleEvents=True,
        orderBy="startTime",
        maxResults=15,
    ).execute()

    items = result.get("items", [])
    print(f"\nAgenda de hoje ({hoje}): {len(items)} evento(s)")
    for ev in items:
        start = ev.get("start", {})
        if "dateTime" in start:
            dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00")).astimezone(_BR)
            hora = dt.strftime("%H:%M")
        else:
            hora = "dia todo"
        titulo = ev.get("summary", "(sem titulo)")
        print(f"  - {hora} - {titulo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
