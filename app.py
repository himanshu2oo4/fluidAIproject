import os
import socket
import time
import logging

from flask import Flask, jsonify
import psycopg2
from psycopg2 import OperationalError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

# Environment vars
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "appdb")
DB_USER = os.environ.get("DB_USER", "appuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

START_TIME = time.time()


def get_db_connection(timeout=2):
    """Attempt a real DB connection. Raises on failure -- caller decides what to do."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=timeout,
    )


@app.route("/")
def index():
    return jsonify({
        "message": "hello from the backend",
        "pod": socket.gethostname(),
        "uptime_seconds": round(time.time() - START_TIME, 1),
    })


@app.route("/healthz")
def liveness():
    """
    LIVENESS probe target.
    Intentionally does NOT check the database.
    If the process can respond to HTTP at all, it is alive.
    A DB outage is not a reason to kill and restart THIS container --
    restarting the app won't fix a dead database, it'll just cause a
    crash-loop on a perfectly healthy process.
    """
    return jsonify({"status": "alive", "pod": socket.gethostname()}), 200


@app.route("/ready")
def readiness():
    """
    READINESS probe target.
    DOES check the database, because a pod that can't reach its DB
    should be pulled out of the Service's load-balancing pool --
    but the pod itself should stay running so it can recover and
    rejoin automatically once the DB is reachable again.
    """
    try:
        conn = get_db_connection(timeout=2)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"status": "ready", "db": "reachable"}), 200
    except OperationalError as e:
        log.warning(f"readiness check failed: {e}")
        return jsonify({"status": "not_ready", "db": "unreachable", "error": str(e)}), 503


@app.route("/work")
def do_work():
    """A pretend endpoint that actually requires the DB to function."""
    try:
        conn = get_db_connection(timeout=2)
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"db_time": str(result[0]), "pod": socket.gethostname()})
    except OperationalError as e:
        log.error(f"DB query failed: {e}")
        return jsonify({"error": "database unavailable", "detail": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
