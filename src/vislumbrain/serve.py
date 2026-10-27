"""Painel no browser: o texto avança, os neurónios acendem e, ao carregar num, vês os contextos onde dispara.

Só biblioteca padrão. Escuta apenas em 127.0.0.1 e recusa pedidos com Host ou Origin que não sejam os do
próprio painel, para outra página aberta no browser não o poder usar.
"""
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import config

WEB = Path(__file__).parent / "web"
MAX_CHARS = 2000
MAX_QUESTION = 200
MAX_BODY = 8192
CSP = ("default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; connect-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def _public(step):
    """Números arredondados e a pontuação em percentagem, que é o que o painel mostra."""
    for lay in step["layers"]:
        for n in lay["neurons"]:
            n["pct"] = round(n.pop("score") * 100, 1)
            n["act"] = round(n["act"], 3)
            n["to_out"] = round(n["to_out"], 2) if "to_out" in n else 0.0
            if n["sense"]:
                n["sense"]["cos"] = round(n["sense"]["cos"], 3)
    for h in step["search"]:
        h["cos"] = round(h["cos"], 3)
    for h in [*step.get("next", []), *([step["actual"]] if step.get("actual") else [])]:
        h["p"] = round(h["p"], 4)
    return step


class Handler(BaseHTTPRequestHandler):
    server_version = "VislumBrain"

    def log_message(self, *_):
        pass

    def _origins(self):
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _headers(self, code, ctype, length=None, nonce=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if nonce:
            self.send_header("Content-Security-Policy", CSP.format(nonce=nonce))
        self.end_headers()

    def _send(self, code, body, ctype="application/json; charset=utf-8", nonce=None):
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode("utf-8")
        self._headers(code, ctype, len(data), nonce)
        self.wfile.write(data)

    def _error(self, code, msg):
        self._send(code, {"error": msg})

    def _guard(self):
        if self.headers.get("Host", "").lower() not in self._origins():
            self._error(403, "pedido recusado")
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/":
            return self._page(q)
        if url.path == "/api/info":
            with self.server.lock:
                return self._send(200, self.server.engine.info())
        if url.path == "/api/neuron":
            try:
                layer, neuron = int(q["layer"]), int(q["neuron"])
                with self.server.lock:
                    return self._send(200, self.server.engine.neuron(layer, neuron))
            except (KeyError, ValueError):
                return self._error(400, "camada ou neurónio inválidos")
        self._error(404, "não existe")

    def _page(self, q):
        nonce = secrets.token_urlsafe(16)
        html = (WEB / "index.html").read_text(encoding="utf-8")
        pre = ""
        if "preload" in q and q.get("text", "").strip():
            text = q["text"].strip()[:MAX_CHARS]
            qa = q.get("mode") == "qa"
            with self.server.lock:
                prefix, prompt = self.server.engine.qa_prompt(text) if qa else ("", text)
                steps = [_public(s) for s in self.server.engine.steps(prompt, self.server.per_layer, with_promotes=True, prefix=prefix)]
                info = self.server.engine.info()
                reply = self.server.engine.reply(prompt, prefix=prefix, short=qa)
            seeded = {}
            try:
                layer, neuron = (int(x) for x in q.get("sel", "").split("."))
                with self.server.lock:
                    seeded[f"{layer}.{neuron}"] = self.server.engine.neuron(layer, neuron)
            except ValueError:
                pass
            blob = json.dumps({"text": text, "info": info, "steps": steps, "neurons": seeded, "reply": reply,
                               "mode": "qa" if qa else "text", "context": prefix, "prompt": prompt}, ensure_ascii=False).replace("<", "\\u003c")
            pre = f'<script type="application/json" id="preload">{blob}</script>'
        self._send(200, html.replace("{{NONCE}}", nonce).replace("{{PRELOAD}}", pre), "text/html; charset=utf-8", nonce)

    def do_POST(self):
        if not self._guard():
            return
        if urlparse(self.path).path != "/api/analyze":
            return self._error(404, "não existe")
        origin = self.headers.get("Origin")
        if origin and origin.removeprefix("http://").lower() not in self._origins():
            return self._error(403, "pedido recusado")
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._error(415, "é preciso JSON")
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._error(400, "pedido inválido")
        if size > MAX_BODY:
            return self._error(413, "pedido grande demais")
        try:
            body = json.loads(self.rfile.read(size))
            text = body["text"].strip()
        except (ValueError, KeyError, AttributeError, TypeError):
            return self._error(400, "falta o texto")
        if not text:
            return self._error(400, "o texto está vazio")
        mode = body.get("mode", "text")
        if mode not in ("text", "qa"):
            return self._error(400, "modo inválido")
        qa = mode == "qa"
        if len(text) > (MAX_QUESTION if qa else MAX_CHARS):
            return self._error(413, f"o texto passa dos {MAX_QUESTION if qa else MAX_CHARS} caracteres")
        self._headers(200, "application/x-ndjson; charset=utf-8")
        try:
            with self.server.lock:
                engine = self.server.engine
                prefix, prompt = engine.qa_prompt(text) if qa else ("", text)
                for step in engine.steps(prompt, self.server.per_layer, with_promotes=True, prefix=prefix):
                    self.wfile.write((json.dumps(_public(step), ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                last = {"reply": engine.reply(prompt, prefix=prefix, short=qa), "context": prefix, "prompt": prompt}
                self.wfile.write((json.dumps(last, ensure_ascii=False) + "\n").encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # a resposta já começou: o erro vai como última linha
            self.wfile.write((json.dumps({"error": f"{type(e).__name__}: {e}"}) + "\n").encode("utf-8"))


def make_server(engine, port=8765, per_layer=config.DEFAULT_PANEL_PER_LAYER):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.engine, srv.lock, srv.per_layer = engine, threading.Lock(), per_layer
    return srv


def run(tag, port=8765, per_layer=config.DEFAULT_PANEL_PER_LAYER, say=print):
    from .engine import Engine
    engine = Engine(tag)
    srv = make_server(engine, port, per_layer)
    say(f"  painel: http://127.0.0.1:{srv.server_address[1]}  (Ctrl+C para parar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        say("  painel parado")
    finally:
        srv.server_close()
