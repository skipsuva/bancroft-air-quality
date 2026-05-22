import logging
import threading

from flask import Flask, jsonify, render_template, request

import db

logger = logging.getLogger(__name__)


def create_app(state: dict, lock: threading.Lock) -> Flask:
    app = Flask(__name__)
    app.logger.setLevel(logging.WARNING)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/now")
    def api_now():
        row = db.get_current()
        if row:
            return jsonify(row)
        with lock:
            return jsonify(dict(state))

    @app.route("/api/history")
    def api_history():
        range_str = request.args.get("range", "24h")
        if range_str not in ("24h", "7d", "30d"):
            return jsonify({"error": "invalid range — use 24h, 7d, or 30d"}), 400
        rows = db.get_history(range_str)
        return jsonify(rows)

    return app
