import logging
import threading

from flask import Flask, jsonify, render_template, request

import config
import db

logger = logging.getLogger(__name__)


def create_app(state: dict, lock: threading.Lock) -> Flask:
    app = Flask(__name__)
    app.logger.setLevel(logging.WARNING)

    @app.route("/")
    def index():
        return render_template("index.html", nodes=config.NODES, node_labels=config.NODE_LABELS)

    @app.route("/api/now")
    def api_now():
        """Return latest readings for ALL nodes as a dict keyed by node name.

        Falls back to the in-memory state for the office node if the DB is empty.
        """
        all_nodes = db.get_all_node_current()

        # Fallback: seed office from in-memory state if DB has no entry yet
        if "office" not in all_nodes:
            row = db.get_current()
            if row:
                row.pop("id", None)  # strip legacy primary key field
                all_nodes["office"] = row
            else:
                with lock:
                    all_nodes["office"] = dict(state)

        return jsonify(all_nodes)

    @app.route("/api/history")
    def api_history():
        range_str = request.args.get("range", "1d")
        node      = request.args.get("node")  # optional; None = all nodes

        valid = {"1d", "1w", "1m", "3m", "6m", "1y", "all", "24h", "7d", "30d"}
        if range_str not in valid:
            return jsonify({"error": "invalid range — use 1d, 1w, 1m, 3m, 6m, 1y, or all"}), 400

        if node and node not in config.NODES:
            return jsonify({"error": f"unknown node — use one of {config.NODES}"}), 400

        rows = db.get_history(range_str, node=node)
        return jsonify(rows)

    return app
