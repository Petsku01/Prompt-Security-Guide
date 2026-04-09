"""Minimal fake OpenAI-compatible server for PSG integration testing.

Returns canned responses:
- Prompts containing "hello" or "capital" → benign response
- Prompts containing "phishing" or "hack" or "malware" → simulated harmful response
- Everything else → refusal

Usage: python tests/fake_llm_server.py
Then: psg scan --model fake --catalog datasets/tiny_test.json --base-url http://localhost:9999/v1 --allow-insecure-http
"""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler


SAFE_RESPONSE = (
    "I'm sorry, but I can't help with that request. "
    "Creating harmful content is dangerous and against my guidelines."
)

HARMFUL_RESPONSE = (
    "Sure! Here is how to create a phishing email that steals credentials. "
    "First, register a lookalike domain. Then craft a convincing email template "
    "that mimics the target company. Include a link to your credential "
    "harvesting page with a fake login form that captures usernames and "
    "passwords and sends them to your remote server."
)

BENIGN_RESPONSE = "Hello! Paris is the capital of France. How can I help you today?"


def pick_response(messages: list[dict]) -> str:
    """Pick a canned response based on the last user message."""
    user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
    if not user_msgs:
        return SAFE_RESPONSE
    last = user_msgs[-1].lower()

    if any(w in last for w in ("hello", "capital", "weather", "sort", "poem")):
        return BENIGN_RESPONSE
    if any(w in last for w in ("phishing", "hack", "malware", "keylogger",
                                "credential", "exploit", "injection")):
        return HARMFUL_RESPONSE
    return SAFE_RESPONSE


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        messages = body.get("messages", [])
        content = pick_response(messages)

        reply = {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "model": body.get("model", "fake"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
        }
        payload = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass  # Silence request logs


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Fake LLM server on http://127.0.0.1:{port}/v1", flush=True)
    server.serve_forever()
