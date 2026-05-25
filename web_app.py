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
        range_str = request.args.get("range", "1d")
        valid = {"1d", "1w", "1m", "3m", "6m", "1y", "all", "24h", "7d", "30d"}
        if range_str not in valid:
            return jsonify({"error": "invalid range — use 1d, 1w, 1m, 3m, 6m, 1y, or all"}), 400
        rows = db.get_history(range_str)
        return jsonify(rows)

    return app
