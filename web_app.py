import logging
import threading

from flask import Flask, jsonify, render_template, request

import config
import db

logger = logging.getLogger(__name__)


def create_app(state: dict, lock: threading.Lock) -> Flask:
    app = Flask(__name__)
    app.logger.setLevel(logging.WARNING)

    _web_labels = {**config.NODE_LABELS, "toddler": "Mari's Room", "wifesoffice": "Em's Office"}

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            nodes=config.NODES,
            node_labels=_web_labels,
            ens160_nodes=config.ENS160_NODES,
        )

    @app.route("/api/now")
    def api_now():
        """Return 5-minute rolling averages for ALL nodes as a dict keyed by node name.

        Falls back to the raw node_current row when fewer than 2 averaged readings
        exist, and to in-memory state for the office node if the DB is empty.
        """
        raw_current = db.get_all_node_current()
        all_nodes = {}

        for node in config.NODES:
            smoothed = db.get_smoothed_current(node)
            if smoothed:
                all_nodes[node] = smoothed
            elif node in raw_current:
                all_nodes[node] = raw_current[node]

        # Legacy fallback: seed office from current_reading table or in-memory state
        if "office" not in all_nodes:
            row = db.get_current()
            if row:
                row.pop("id", None)
                all_nodes["office"] = row
            else:
                with lock:
                    all_nodes["office"] = dict(state)

        return jsonify(all_nodes)

    @app.route("/api/history")
    def api_history():
        range_str = request.args.get("range", "1d")
        node      = request.args.get("node")   # optional; None = all nodes
        smooth    = request.args.get("smooth", "0") == "1"

        valid = {"2h", "6h", "1d", "1w", "1m", "3m", "6m", "1y", "all", "24h", "7d", "30d"}
        if range_str not in valid:
            return jsonify({"error": "invalid range — use 1d, 1w, 1m, 3m, 6m, 1y, or all"}), 400

        if node and node not in config.NODES:
            return jsonify({"error": f"unknown node — use one of {config.NODES}"}), 400

        rows = db.get_history(range_str, node=node, smooth=smooth)
        return jsonify(rows)

    return app
