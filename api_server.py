"""
api_server.py — Flask API standalone para o SysHealth.
Expõe dados do banco via HTTP para consumo externo (ex: Hermes Lite).
Porta: 5060
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request
from db import query

app = Flask(__name__)
_TZ = ZoneInfo("America/Sao_Paulo")


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def _hoje() -> str:
    return datetime.now(_TZ).date().isoformat()


def _v(val, default=None):
    """Normaliza valor de célula pandas: NaN → default, numpy scalar → Python nativo."""
    if val is None:
        return default
    if isinstance(val, float) and math.isnan(val):
        return default
    return val.item() if hasattr(val, "item") else val


def _scalar(df, col, default=None):
    """Extrai primeiro valor de uma coluna de DataFrame de linha única."""
    try:
        return _v(df[col].iloc[0], default)
    except Exception:
        return default


# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/resumo")
def resumo():
    hoje = _hoje()
    result = {
        "agua_hoje_ml": None,
        "peso_kg": None,
        "sono_horas": None,
        "passos_hoje": None,
        "treino_hoje": None,
        "deficit_calorico": None,
        "proteina_g": None,
        "carboidrato_g": None,
        "hrv": None,
        "fadiga": None,
        "tirzepatida_hoje": False,
        "offline": False,
    }

    try:
        df = query(
            "SELECT SUM(quantidade_ml) AS total FROM agua "
            "WHERE date(data_hora,'localtime') = ?",
            [hoje],
        )
        result["agua_hoje_ml"] = _scalar(df, "total")
    except Exception:
        pass

    try:
        df = query("SELECT peso FROM medidas ORDER BY data DESC, id DESC LIMIT 1")
        result["peso_kg"] = _scalar(df, "peso")
    except Exception:
        pass

    _calorias_gastas = None
    try:
        df = query(
            "SELECT sono_total_min, passos, hrv_ms, calorias_gastas FROM amazfit_dados "
            "WHERE date(data_hora,'localtime') = ? LIMIT 1",
            [hoje],
        )
        if not df.empty:
            sono_min = _scalar(df, "sono_total_min")
            if sono_min:
                result["sono_horas"] = round(sono_min / 60.0, 1)
            result["passos_hoje"] = _scalar(df, "passos")
            hrv_raw = _scalar(df, "hrv_ms")
            result["hrv"] = int(hrv_raw) if hrv_raw else None
            _calorias_gastas = _scalar(df, "calorias_gastas")
    except Exception:
        pass

    try:
        df = query(
            "SELECT titulo FROM hevy_treinos "
            "WHERE date(data_hora,'localtime') = ? "
            "ORDER BY data_hora DESC LIMIT 1",
            [hoje],
        )
        if not df.empty:
            result["treino_hoje"] = _scalar(df, "titulo")
    except Exception:
        pass

    try:
        df = query(
            "SELECT SUM(calorias) AS cal, SUM(proteinas) AS prot, SUM(carboidratos) AS carb "
            "FROM refeicoes WHERE date(data_hora,'localtime') = ?",
            [hoje],
        )
        prot = _scalar(df, "prot")
        result["proteina_g"] = round(float(prot), 1) if prot is not None else None
        carb = _scalar(df, "carb")
        result["carboidrato_g"] = round(float(carb), 1) if carb is not None else None
        cal_consumidas = _scalar(df, "cal")
        if _calorias_gastas is not None and cal_consumidas is not None:
            result["deficit_calorico"] = int(_calorias_gastas - cal_consumidas)
    except Exception:
        pass

    try:
        df = query(
            "SELECT COUNT(*) AS cnt FROM medicacao "
            "WHERE date(data_hora,'localtime') = ?",
            [hoje],
        )
        cnt = _scalar(df, "cnt", 0)
        result["tirzepatida_hoje"] = bool(cnt and cnt > 0)
    except Exception:
        pass

    return jsonify(result)


@app.route("/api/treinos")
def treinos():
    try:
        dias = int(request.args.get("dias", 7))
    except (TypeError, ValueError):
        dias = 7

    try:
        cutoff = (datetime.now(_TZ).date() - timedelta(days=dias)).isoformat()
        df = query(
            "SELECT data_hora AS data, titulo, duracao_min, volume_kg "
            "FROM hevy_treinos "
            "WHERE date(data_hora,'localtime') >= ? "
            "ORDER BY data_hora DESC",
            [cutoff],
        )
        rows = [
            {
                "data": str(row["data"]),
                "titulo": _v(row["titulo"]),
                "duracao_min": _v(row["duracao_min"]),
                "volume_kg": _v(row["volume_kg"]),
            }
            for _, row in df.iterrows()
        ]
        return jsonify(rows)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/treinos/analise")
def treinos_analise():
    try:
        dias = int(request.args.get("dias", 30))
    except (TypeError, ValueError):
        dias = 30

    result = {
        "periodo_dias": dias,
        "total_treinos": 0,
        "volume_total_kg": None,
        "duracao_media_min": None,
        "treinos_por_semana": None,
        "ultimo_treino": None,
        "exercicios_frequentes": [],
        "grupos_musculares": {},
    }

    try:
        cutoff = (datetime.now(_TZ).date() - timedelta(days=dias)).isoformat()
        df = query(
            "SELECT data_hora, duracao_min, volume_kg, exercicios_json "
            "FROM hevy_treinos "
            "WHERE data_hora >= ? "
            "ORDER BY data_hora DESC",
            [cutoff],
        )
        if not df.empty:
            result["total_treinos"] = len(df)

            try:
                vol = df["volume_kg"].dropna()
                result["volume_total_kg"] = round(float(vol.sum()), 2) if not vol.empty else None
            except Exception:
                pass

            try:
                dur = df["duracao_min"].dropna()
                result["duracao_media_min"] = round(float(dur.mean())) if not dur.empty else None
            except Exception:
                pass

            try:
                result["treinos_por_semana"] = round(len(df) / (dias / 7), 1)
            except Exception:
                pass

            try:
                result["ultimo_treino"] = str(df["data_hora"].iloc[0])[:10]
            except Exception:
                pass

            try:
                contagem = defaultdict(lambda: {"vezes": 0, "carga_max_kg": 0.0})
                for raw in df["exercicios_json"].dropna():
                    try:
                        exs = raw if isinstance(raw, list) else json.loads(raw)
                        if not isinstance(exs, list):
                            continue
                        for ex in exs:
                            titulo = ex.get("titulo") or ex.get("title") or ex.get("name") or ""
                            if not titulo:
                                continue
                            contagem[titulo]["vezes"] += 1
                            sets = ex.get("sets") or ex.get("series") or []
                            for s in sets:
                                try:
                                    peso = float(s.get("weight_kg") or s.get("peso_kg") or s.get("carga_kg") or 0)
                                except (TypeError, ValueError):
                                    peso = 0.0
                                if peso > contagem[titulo]["carga_max_kg"]:
                                    contagem[titulo]["carga_max_kg"] = peso
                    except Exception:
                        continue
                top10 = sorted(contagem.items(), key=lambda x: x[1]["vezes"], reverse=True)[:10]
                result["exercicios_frequentes"] = [
                    {"titulo": t, "vezes": v["vezes"], "carga_max_kg": v["carga_max_kg"]}
                    for t, v in top10
                ]
            except Exception:
                pass

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.route("/api/corpo")
def corpo():
    try:
        dias = int(request.args.get("dias", 90))
    except (TypeError, ValueError):
        dias = 90

    result = {
        "peso_atual": None,
        "peso_inicial": None,
        "variacao_kg": None,
        "historico": [],
    }

    try:
        cutoff = (datetime.now(_TZ).date() - timedelta(days=dias)).isoformat()
        df = query(
            "SELECT data, peso, cintura FROM medidas "
            "WHERE date(data) >= ? "
            "ORDER BY data DESC",
            [cutoff],
        )
        if not df.empty:
            try:
                result["peso_atual"] = _v(df["peso"].iloc[0])
            except Exception:
                pass
            try:
                result["peso_inicial"] = _v(df["peso"].iloc[-1])
            except Exception:
                pass
            try:
                if result["peso_atual"] is not None and result["peso_inicial"] is not None:
                    result["variacao_kg"] = round(result["peso_atual"] - result["peso_inicial"], 2)
            except Exception:
                pass
            try:
                result["historico"] = [
                    {
                        "data": str(row["data"])[:10],
                        "peso": _v(row["peso"]),
                        "cintura": _v(row["cintura"]),
                    }
                    for _, row in df.iterrows()
                ]
            except Exception:
                pass

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.route("/api/sono")
def sono():
    try:
        dias = int(request.args.get("dias", 14))
    except (TypeError, ValueError):
        dias = 14

    result = {
        "media_sono_min": None,
        "media_sono_profundo_min": None,
        "media_hrv": None,
        "media_pai": None,
        "historico": [],
    }

    try:
        cutoff = (datetime.now(_TZ).date() - timedelta(days=dias)).isoformat()
        df = query(
            "SELECT data_hora, sono_total_min, sono_profundo_min, hrv_ms, passos, pai "
            "FROM amazfit_dados "
            "WHERE data_hora >= ? "
            "ORDER BY data_hora DESC",
            [cutoff],
        )
        if not df.empty:
            try:
                sono_vals = df["sono_total_min"].dropna()
                result["media_sono_min"] = round(float(sono_vals.mean())) if not sono_vals.empty else None
            except Exception:
                pass
            try:
                profundo_vals = df["sono_profundo_min"].dropna()
                result["media_sono_profundo_min"] = round(float(profundo_vals.mean())) if not profundo_vals.empty else None
            except Exception:
                pass
            try:
                hrv_vals = df["hrv_ms"].dropna()
                result["media_hrv"] = round(float(hrv_vals.mean())) if not hrv_vals.empty else None
            except Exception:
                pass
            try:
                pai_vals = df["pai"].dropna()
                result["media_pai"] = round(float(pai_vals.mean())) if not pai_vals.empty else None
            except Exception:
                pass
            try:
                result["historico"] = [
                    {
                        "data": str(row["data_hora"])[:10],
                        "sono_min": _v(row["sono_total_min"]),
                        "sono_profundo_min": _v(row["sono_profundo_min"]),
                        "hrv": _v(row["hrv_ms"]),
                        "passos": _v(row["passos"]),
                        "pai": _v(row["pai"]),
                    }
                    for _, row in df.iterrows()
                ]
            except Exception:
                pass

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.route("/api/corridas")
def corridas():
    try:
        dias = int(request.args.get("dias", 30))
    except (TypeError, ValueError):
        dias = 30

    result = {
        "total_corridas": 0,
        "distancia_total_km": None,
        "historico": [],
    }

    try:
        cutoff = (datetime.now(_TZ).date() - timedelta(days=dias)).isoformat()
        df = query(
            "SELECT data_hora, corrida_km, corrida_cal "
            "FROM amazfit_dados "
            "WHERE corrida_km > 0 AND data_hora >= ? "
            "ORDER BY data_hora DESC",
            [cutoff],
        )
        if not df.empty:
            result["total_corridas"] = len(df)
            try:
                dist = df["corrida_km"].dropna()
                result["distancia_total_km"] = round(float(dist.sum()), 2) if not dist.empty else None
            except Exception:
                pass
            try:
                result["historico"] = [
                    {
                        "data": str(row["data_hora"])[:10],
                        "distancia_km": _v(row["corrida_km"]),
                        "calorias": _v(row["corrida_cal"]),
                    }
                    for _, row in df.iterrows()
                ]
            except Exception:
                pass

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


# ── Entry point ───────────────────────────────────────────────────────────────
# Não chame app.run() no import — Streamlit Cloud executa apenas dashboard.py.
# Flask usa Werkzeug aqui (porta 5060); não há uvicorn neste projeto.

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5060, debug=False)
