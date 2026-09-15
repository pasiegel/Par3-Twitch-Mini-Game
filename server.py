#!/usr/bin/env python3
"""
Par 3 - Local stats backend.

Zero-dependency HTTP server (stdlib only) that persists player stats to a
StreamData\\par3_stats.json folder next to this script/exe, for the index.html
OBS browser source to read/write. Portable: copy this + index.html anywhere
(including another machine) and the stats folder travels alongside it.

Run:
    python server.py
    python server.py --port 6000
    (or the packaged server.exe - see README.md "Portable / standalone exe")

If you change the port, also update API_BASE near the top of index.html's
<script> block to match, or the frontend won't find this server.

Endpoints:
    GET  /load_stats  -> returns the full stats JSON object (creates file/dir if missing)
    POST /save_stats  -> overwrites the stats file with the posted JSON body
    OPTIONS *          -> CORS preflight response for the above
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "localhost"
DEFAULT_PORT = 5000

# sys.executable is the actual server.exe path when frozen by PyInstaller
# (sys.argv[0]/__file__ would instead point into its temp extraction dir).
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATS_DIR = os.path.join(BASE_DIR, "StreamData")
STATS_PATH = os.path.join(STATS_DIR, "par3_stats.json")


def ensure_stats_file():
    """Create the StreamData directory and an empty stats file if they don't exist yet."""
    os.makedirs(STATS_DIR, exist_ok=True)
    if not os.path.isfile(STATS_PATH):
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)


def read_stats():
    ensure_stats_file()
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # Corrupt/empty file - treat as a fresh stats object rather than crashing the server.
            return {}


def write_stats(data):
    ensure_stats_file()
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class Par3Handler(BaseHTTPRequestHandler):
    # Quiet the default request logging noise; comment out to debug.
    def log_message(self, format, *args):
        pass

    def _send_cors_headers(self):
        # OBS Browser Source (and a plain browser during dev) fetches this as a
        # different-origin request, so every response needs these headers.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # CORS preflight - no body needed.
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/load_stats":
            self._send_json(200, read_stats())
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/save_stats":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid json"})
                return
            write_stats(data)
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="Par 3 local stats backend.")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT}). Update API_BASE in "
             f"index.html to match if you change this."
    )
    args = parser.parse_args()

    ensure_stats_file()
    server = HTTPServer((HOST, args.port), Par3Handler)
    print(f"Par 3 stats server running at http://{HOST}:{args.port}")
    print(f"Stats file: {STATS_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
