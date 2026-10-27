import http.client
import json
import threading
import unittest

from vislumbrain import serve


class FakeEngine:
    def info(self):
        return {"tag": "t", "layers": [3, 7, 11]}

    def qa_prompt(self, question):
        return "", f"Q: {question}\nA:"

    def steps(self, text, per_layer=5, max_lit=None, with_promotes=False, prefix=""):
        for i, w in enumerate(text.split()):
            yield {"i": i, "piece": w, "window": w,
                   "layers": [{"layer": 3, "neurons": [{"neuron": 1, "act": 1.23456, "score": 0.5, "lit": True,
                                                         "to_out": -1.23456, "sense": None, "promotes": None}]}],
                   "search": [], "next": [{"piece": "x", "p": 0.123456}], "actual": {"piece": "y", "p": 0.05555}}

    def reply(self, text, prefix="", short=False):
        return ["▁ok", "."] if not short else ["▁resposta"]

    def neuron(self, layer, neuron):
        if layer != 3:
            raise ValueError("fora")
        return {"layer": layer, "neuron": neuron, "contexts": []}


class Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serve.make_server(FakeEngine(), port=0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def call(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        h = {"Content-Type": "application/json", **(headers or {})}
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        return r.status, r.getheader("Content-Security-Policy"), r.read().decode("utf-8")

    def test_page_has_nonce_csp(self):
        code, csp, html = self.call("GET", "/")
        self.assertEqual(code, 200)
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertIn(f'nonce="{nonce}"', html)
        self.assertNotIn("{{", html)

    def test_foreign_host_rejected(self):
        self.assertEqual(self.call("GET", "/api/info", headers={"Host": "evil.example"})[0], 403)

    def test_foreign_origin_rejected(self):
        code, _, _ = self.call("POST", "/api/analyze", json.dumps({"text": "a b"}), {"Origin": "http://evil.example"})
        self.assertEqual(code, 403)

    def test_bad_neuron_params(self):
        self.assertEqual(self.call("GET", "/api/neuron?layer=x&neuron=1")[0], 400)
        self.assertEqual(self.call("GET", "/api/neuron?layer=3")[0], 400)
        self.assertEqual(self.call("GET", "/api/neuron?layer=9&neuron=1")[0], 400)

    def test_long_text_413(self):
        code, _, _ = self.call("POST", "/api/analyze", json.dumps({"text": "a" * (serve.MAX_CHARS + 1)}))
        self.assertEqual(code, 413)

    def test_empty_text_400(self):
        self.assertEqual(self.call("POST", "/api/analyze", json.dumps({"text": "  "}))[0], 400)

    def test_ndjson_stream(self):
        code, _, body = self.call("POST", "/api/analyze", json.dumps({"text": "um dois tres"}))
        rows = [json.loads(x) for x in body.splitlines()]
        self.assertEqual((code, len(rows)), (200, 4))
        self.assertEqual(rows[-1], {"reply": ["▁ok", "."], "context": "", "prompt": "um dois tres"})

    def test_qa_mode_and_bad_mode(self):
        code, _, body = self.call("POST", "/api/analyze", json.dumps({"text": "Capital?", "mode": "qa"}))
        rows = [json.loads(x) for x in body.splitlines()]
        self.assertEqual((code, rows[-1]["reply"]), (200, ["▁resposta"]))
        self.assertEqual(rows[-1]["prompt"], "Q: Capital?\nA:")
        self.assertEqual(self.call("POST", "/api/analyze", json.dumps({"text": "a", "mode": "x"}))[0], 400)
        long_q = json.dumps({"text": "a" * (serve.MAX_QUESTION + 1), "mode": "qa"})
        self.assertEqual(self.call("POST", "/api/analyze", long_q)[0], 413)
        self.assertEqual(rows[0]["layers"][0]["neurons"][0]["pct"], 50.0)
        self.assertNotIn("score", rows[0]["layers"][0]["neurons"][0])
        self.assertEqual(rows[0]["layers"][0]["neurons"][0]["to_out"], -1.23)
        self.assertEqual((rows[0]["next"][0]["p"], rows[0]["actual"]["p"]), (0.1235, 0.0556))


if __name__ == "__main__":
    unittest.main()
