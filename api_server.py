"""
api_server.py — Flask API standalone para o SysHealth.
Expõe dados do banco via HTTP para consumo externo (ex: Hermes Lite).
Porta: 5060
"""
import math
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
        "agua": None,
        "peso": None,
        "sono": None,
        "passos": None,
        "treino": None,
        "deficit": None,
        "proteina": None,
        "tirzepatida": False,
        "offline": False,
    }

    try:
        df = query(
            "SELECT SUM(quantidade_ml) AS total FROM agua "
            "WHERE date(data_hora,'localtime') = ?",
            [hoje],
        )
        result["agua"] = _scalar(df, "total")
    except Exception:
        pass

    try:
        df = query("SELECT peso FROM medidas ORDER BY id DESC LIMIT 1")
        result["peso"] = _scalar(df, "peso")
    except Exception:
        pass

    try:
        df = query(
            "SELECT sono_total_min, passos FROM amazfit_dados "
            "WHERE date(data_hora,'localtime') = ? LIMIT 1",
            [hoje],
        )
        if not df.empty:
            result["sono"] = _scalar(df, "sono_total_min")
            result["passos"] = _scalar(df, "passos")
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
            result["treino"] = _scalar(df, "titulo")
    except Exception:
        pass

    try:
        df = query(
            "SELECT SUM(proteinas) AS total FROM refeicoes "
            "WHERE date(data_hora,'localtime') = ?",
            [hoje],
        )
        result["proteina"] = _scalar(df, "total")
    except Exception:
        pass

    try:
        df = query(
            "SELECT COUNT(*) AS cnt FROM medicacao "
            "WHERE date(data_hora,'localtime') = ?",
            [hoje],
        )
        cnt = _scalar(df, "cnt", 0)
        result["tirzepatida"] = bool(cnt and cnt > 0)
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


# ── Entry point ───────────────────────────────────────────────────────────────
# Não chame app.run() no import — Streamlit Cloud executa apenas dashboard.py.
# Flask usa Werkzeug aqui (porta 5060); não há uvicorn neste projeto.

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5060, debug=False)
