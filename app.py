import json
import os
import time
from pathlib import Path
from functools import wraps
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
API_KEY = os.getenv("API_KEY", "")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))
BRIDGE_DIR = Path(os.getenv("BRIDGE_DIR", "./bridge")).expanduser()
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

STATE = BRIDGE_DIR / "state.json"
TRADES = BRIDGE_DIR / "trades.json"
COMMAND = BRIDGE_DIR / "desired_state.json"
ALERTS = BRIDGE_DIR / "alerts.json"


def read_json(path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(path)


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not API_KEY:
            return jsonify({"error": "Server is not configured: API_KEY is empty"}), 500
        supplied = request.headers.get("Authorization", "")
        if supplied != f"Bearer {API_KEY}":
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.get("/health")
def health():
    return jsonify({"service": "ok", "timestamp": int(time.time())})


@app.get("/api/status")
@auth_required
def status():
    state = read_json(STATE, {})
    return jsonify({
        "service": "ok",
        "robot": state,
        "updated": state.get("updated", 0),
    })


@app.get("/api/trades")
@auth_required
def trades():
    return jsonify(read_json(TRADES, {"trades": []}))


@app.get("/api/account")
@auth_required
def account():
    state = read_json(STATE, {})
    return jsonify({
        "balance": state.get("balance", 0),
        "equity": state.get("equity", 0),
        "currency": state.get("currency", ""),
    })


@app.get("/api/alerts")
@auth_required
def alerts():
    return jsonify(read_json(ALERTS, {"alerts": []}))


@app.post("/api/robot/start")
@auth_required
def start():
    write_json(COMMAND, {"enabled": True, "requestedAt": int(time.time())})
    return jsonify({"ok": True, "command": "start"})


@app.post("/api/robot/stop")
@auth_required
def stop():
    write_json(COMMAND, {"enabled": False, "requestedAt": int(time.time())})
    return jsonify({"ok": True, "command": "stop"})


if __name__ == "__main__":
    # Development server only. Use a production WSGI server/reverse proxy on a real VPS.
    app.run(host=HOST, port=PORT, debug=False)
