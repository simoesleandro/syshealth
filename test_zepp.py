"""
test_zepp.py — diagnóstico rápido da API Zepp
Rode com: python test_zepp.py
Não sobe bot, não causa conflito 409.
"""
import os, json, base64, requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

TOKEN   = os.getenv("ZEPP_APP_TOKEN", "").strip()
USER_ID = os.getenv("ZEPP_USER_ID", "").strip()
TODAY   = date.today().strftime("%Y-%m-%d")

print("=" * 55)
print(f"  SYS.HEALTH — Diagnóstico Zepp")
print("=" * 55)
print(f"  Data:    {TODAY}")
print(f"  Token:   {TOKEN[:12]}...{TOKEN[-6:] if len(TOKEN) > 18 else '(curto!)'}")
print(f"  UserID:  {USER_ID}")
print("=" * 55)

if not TOKEN or not USER_ID:
    print("\n❌ ZEPP_APP_TOKEN ou ZEPP_USER_ID não encontrados no .env")
    exit(1)

headers = {
    "Accept": "*/*",
    "appname": "com.huami.midong",
    "appplatform": "ios_phone",
    "apptoken": TOKEN,
    "channel": "appstore",
    "country": "BR",
    "lang": "pt_BR",
    "timezone": "America/Sao_Paulo",
    "User-Agent": "Zepp/10.3.1 (iPhone; iOS 26.4.2; Scale/3.00)",
    "v": "2.0",
}

params = {
    "query_type": "summary",
    "device_type": "0",
    "object_id": USER_ID,
    "from_date": TODAY,
    "to_date": TODAY,
}

print("\n⏳ Chamando a API do Zepp...")
try:
    r = requests.get(
        "https://api-mifit-us3.zepp.com/v1/data/band_data.json",
        headers=headers,
        params=params,
        timeout=15,
    )
    print(f"\n  HTTP Status: {r.status_code}")
    print(f"  Resposta bruta:\n")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))

        code  = data.get("code")
        msg   = data.get("message", "")
        items = data.get("data", [])

        print("\n" + "=" * 55)
        if r.status_code != 200:
            print(f"❌ ERRO HTTP {r.status_code}")
        elif code not in (1, "1", 0, "0"):
            print(f"❌ TOKEN INVÁLIDO OU EXPIRADO")
            print(f"   code={code}  msg={msg}")
            print("\n   → Abra o app Zepp no celular e pegue um novo token.")
        elif not items:
            print(f"⚠️  TOKEN OK mas sem dados para hoje ({TODAY})")
            print(f"   code={code}  msg={msg}")
            print("\n   → O relógio ainda não sincronizou com o app hoje.")
            print("   → Abra o Zepp no celular e force a sincronização.")
        else:
            # Decodifica o summary
            b64 = items[0].get("summary", "")
            pad = b64 + "=" * (4 - len(b64) % 4)
            s   = json.loads(base64.b64decode(pad).decode("utf-8", "replace"))
            stp = s.get("stp", {}) or {}
            slp = s.get("slp", {}) or {}
            deep = int(slp.get("dp", 0) or 0)
            lt   = int(slp.get("lt", 0) or 0)
            rem  = int(slp.get("dt", 0) or 0)
            tot  = deep + lt + rem or int(slp.get("ebt", 0) or 0)

            print(f"✅ DADOS OK!")
            print(f"   Passos:        {stp.get('ttl', 0):,}")
            print(f"   Calorias:      {stp.get('cal', 0):,} kcal")
            print(f"   Distância:     {int(stp.get('dis', 0)) / 1000:.2f} km")
            print(f"   Sono total:    {tot // 60}h{tot % 60:02d}")
            print(f"   Sono profundo: {deep // 60}h{deep % 60:02d}")
            print(f"\n   → Salvando no banco de dados...")
            try:
                import db as DB
                day_key = f"{TODAY} 00:00:00"
                # Preserva HRV/PAI existentes
                df_ex = DB.query(
                    "SELECT hrv_ms, pai FROM amazfit_dados WHERE data_hora=?",
                    [day_key]
                )
                hrv_ex = int(df_ex["hrv_ms"].iloc[0]) if not df_ex.empty else 0
                pai_ex = int(df_ex["pai"].iloc[0])    if not df_ex.empty else 0

                row = {
                    "data_hora":         day_key,
                    "passos":            int(stp.get("ttl", 0) or 0),
                    "calorias_gastas":   int(stp.get("cal", 0) or 0),
                    "distancia_km":      round(int(stp.get("dis", 0) or 0) / 1000, 2),
                    "sono_total_min":    tot,
                    "sono_profundo_min": deep,
                    "hrv_ms":            hrv_ex,
                    "pai":               pai_ex,
                }
                DB.execute("DELETE FROM amazfit_dados WHERE data_hora=?", [day_key])
                DB.execute(
                    "INSERT INTO amazfit_dados VALUES (?,?,?,?,?,?,?,?)",
                    [row["data_hora"], row["passos"], row["calorias_gastas"],
                     row["distancia_km"], row["sono_total_min"], row["sono_profundo_min"],
                     row["hrv_ms"], row["pai"]]
                )
                print(f"   ✅ Salvo no banco! HRV/PAI preservados: {hrv_ex}ms / {pai_ex}")
                print(f"\n   → Dashboard já vai mostrar os dados atualizados.")
            except Exception as db_err:
                print(f"   ❌ Erro ao salvar no banco: {db_err}")
                print(f"   → Verifique SUPABASE_URL no .env")

    except Exception:
        print(r.text[:500])

except requests.Timeout:
    print("\n❌ TIMEOUT — servidor Zepp não respondeu em 15s")
except requests.ConnectionError as e:
    print(f"\n❌ ERRO DE CONEXÃO: {e}")

print("\n" + "=" * 55)
