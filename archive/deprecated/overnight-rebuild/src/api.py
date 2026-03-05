"""Zero-dependency HTTP API + GUI server for the LLM security testing tool.

Usage:
  python api.py --host 127.0.0.1 --port 8787

Endpoints:
  GET  /        -> serves gui/index.html
  POST /run     -> runs attack battery, returns JSON
  POST /test    -> tests single custom prompt, returns JSON
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cli import OpenAICompatClient
from core.analyzer import ResponseAnalyzer
from core.fingerprinter import Fingerprinter
from core.runner import AttackRunner


SRC_DIR = Path(__file__).resolve().parent
GUI_INDEX = SRC_DIR / "gui" / "index.html"
CATALOG_PATH = SRC_DIR / "attacks" / "catalog.json"


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _get_api_key(self) -> str | None:
        """Extract API key from Authorization header or env."""
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip() or None
        return os.getenv("LLM_API_KEY")

    def _get_base_url(self) -> str:
        """Get LLM base URL from env."""
        return os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            if GUI_INDEX.exists():
                self._send_html(200, GUI_INDEX.read_text(encoding="utf-8"))
            else:
                self._send_html(404, "<h1>GUI not found</h1>")
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        
        if path == "/run":
            self._handle_run()
        elif path == "/test":
            self._handle_test()
        else:
            self._send_json(404, {"error": "Not found"})

    def _parse_json_body(self) -> dict | None:
        """Parse JSON body, return None on error."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            self._send_json(400, {"error": "Invalid JSON payload"})
            return None

    def _handle_run(self) -> None:
        """Handle POST /run - run attack battery."""
        payload = self._parse_json_body()
        if payload is None:
            return

        model = (payload.get("model") or "").strip()
        battery = payload.get("battery") or "minimum"
        known_type = payload.get("known_type")  # Optional: skip fingerprint

        if not model:
            self._send_json(400, {"error": "model is required"})
            return
        if battery not in {"minimum", "standard", "full"}:
            self._send_json(400, {"error": "battery must be one of: minimum, standard, full"})
            return

        base_url = self._get_base_url()
        api_key = self._get_api_key()

        client = OpenAICompatClient(base_url=base_url, api_key=api_key)
        runner = AttackRunner(catalog_path=CATALOG_PATH)

        # Fingerprint (skip if known_type provided)
        if known_type:
            fingerprint = {
                "model": model,
                "matched_signature": known_type,
                "confidence": 1.0,
                "features": {"user_provided": True},
            }
        else:
            fingerprint = Fingerprinter().fingerprint(client=client, model=model)

        raw_results = runner.run(client=client, model=model, battery=battery)
        analyzed = ResponseAnalyzer().analyze_batch(raw_results)
        analyzed["fingerprint"] = fingerprint

        self._send_json(200, analyzed)

    def _handle_test(self) -> None:
        """Handle POST /test - test single custom prompt."""
        payload = self._parse_json_body()
        if payload is None:
            return

        model = (payload.get("model") or "").strip()
        prompt = (payload.get("prompt") or "").strip()

        if not model:
            self._send_json(400, {"error": "model is required"})
            return
        if not prompt:
            self._send_json(400, {"error": "prompt is required"})
            return

        base_url = self._get_base_url()
        api_key = self._get_api_key()

        client = OpenAICompatClient(base_url=base_url, api_key=api_key)
        
        # Send prompt to model
        response = client.chat(model=model, messages=[{"role": "user", "content": prompt}])
        
        # Analyze response
        analysis = ResponseAnalyzer().analyze_one(response)

        self._send_json(200, {
            "model": model,
            "prompt": prompt,
            "response": response,
            "analysis": analysis,
        })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve GUI + /run API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Serving LLM Security Tester on http://{args.host}:{args.port}")
    print(f"LLM Backend: {os.getenv('LLM_BASE_URL', 'http://localhost:11434/v1')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
