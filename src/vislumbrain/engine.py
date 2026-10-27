"""Motor partilhado pela vista no terminal (live) e pelo painel no browser (serve).

Carrega o modelo, o embedder e o Qdrant uma só vez. Para cada token do texto diz que neurónios
acendem em cada camada e em que sentido estão a ser usados, e para um neurónio dá os contextos onde
já tinha acendido forte.
"""
import json
from collections import defaultdict

import numpy as np
import torch

from . import config
from .embed import Embedder
from .model import Recorder, load, n_neurons, ref_from_label, writes_to
from .store import Store
from .util import show_piece


NEXT_K = 5
REPLY_TOKENS = 28
SHORT_TOKENS = 10


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


class Engine:
    def __init__(self, tag):
        self.tag = tag
        base = config.DATA_DIR / tag
        meta = json.loads((base / "scan_meta.json").read_text(encoding="utf-8"))
        self.tok, self.model = load(ref_from_label(meta["model"]))
        self.emb, self.store = Embedder(), Store(tag, reader=True)
        stats = np.load(base / "stats.npz")
        self.layers = [int(x) for x in stats["layers"]]
        self.peak = torch.from_numpy(stats["max"])
        self.min_act = meta["min_act"]
        self.n_neurons = n_neurons(self.model)
        self._base = base
        self._ctx = self._senses = None
        self._writes = {}

    def info(self):
        return {"tag": self.tag, "layers": self.layers, "min_act": self.min_act, "version": config.VERSION,
                "credits": config.CREDITS, "neurons_per_layer": self.n_neurons}

    def _promotes(self, layer, neuron, k=3):
        key = (layer, neuron, k)
        if key not in self._writes:
            up, down = writes_to(self.model, self.tok, layer, neuron, k)
            self._writes[key] = ([show_piece(x) for x in up], [show_piece(x) for x in down])
        return self._writes[key]

    def _sense(self, vec, layer, neuron):
        hit = self.store.query(self.store.sen, vec, limit=1, layer=layer, neuron=neuron)
        if not hit:
            return None
        p = hit[0].payload
        return {"sense": p["sense"] + 1, "n_senses": p["n_senses"], "cos": float(hit[0].score),
                "example": p["example"]}

    def _ids(self, text, prefix=""):
        head = self.tok.encode(prefix) if prefix else []
        return [self.tok.eos_token_id] + head + self.tok.encode(text)[:config.BLOCK_TOKENS - 1], 1 + len(head)

    def steps(self, text, per_layer=5, max_lit=None, with_promotes=False, prefix=""):
        """Um dicionário por token. Em cada camada, os per_layer neurónios com maior fracção do seu máximo.

        'lit' é verdadeiro quando o neurónio passa o limiar de actividade do scan. O sentido só é
        procurado nos max_lit mais fortes (todos, se for None), porque cada um custa uma pesquisa.
        O prefix é lido pelo modelo mas não é mostrado token a token (os exemplos do modo pergunta)."""
        ids, first = self._ids(text, prefix)
        if len(ids) <= first:
            return
        with torch.no_grad(), Recorder(self.model, self.layers) as rec:
            logits = self.model(torch.tensor([ids])).logits[0]
        wte = self.model.transformer.wte.weight.detach()
        for t in range(first, len(ids)):
            probs = torch.softmax(logits[t].detach(), dim=-1)
            top_p, top_i = probs.topk(NEXT_K)
            best = wte[int(top_i[0])]
            nxt = [{"piece": show_piece(self.tok.decode([int(i)])), "p": float(p)} for p, i in zip(top_p, top_i)]
            actual = ({"piece": show_piece(self.tok.decode([ids[t + 1]])), "p": float(probs[ids[t + 1]])}
                      if t + 1 < len(ids) else None)
            window = self.tok.decode(ids[max(first, t - config.WINDOW_LEFT):t + 1])
            vec = self.emb.encode([window])[0]
            layers = []
            for li, layer in enumerate(self.layers):
                act, peak = rec.acts[layer][0, t], self.peak[li]
                score = torch.where(peak >= self.min_act, act / peak.clamp(min=1e-6), torch.zeros_like(act))
                col = []
                for s, n in zip(*score.topk(per_layer)):
                    n = int(n)
                    lit = bool(act[n] >= self.min_act and peak[n] >= self.min_act)
                    # efeito directo no 1.º classificado: activação x (linha de c_proj . embedding do token).
                    # Ignora a normalização final e as camadas seguintes, por isso é uma aproximação.
                    push = float(act[n] * (self.model.transformer.h[layer].mlp.c_proj.weight[n].detach() @ best))
                    col.append({"neuron": n, "act": float(act[n]), "score": float(s), "lit": lit,
                                "to_out": push, "sense": None, "promotes": None})
                layers.append({"layer": layer, "neurons": col})
            strongest = sorted(((n["score"], lay["layer"], n) for lay in layers for n in lay["neurons"] if n["lit"]),
                               key=lambda x: -x[0])
            for _score, layer, n in strongest[:max_lit]:
                n["sense"] = self._sense(vec, layer, n["neuron"])
                if with_promotes:
                    n["promotes"] = self._promotes(layer, n["neuron"])[0]
            search = []
            for h in self.store.query(self.store.sen, vec, limit=3):
                p = h.payload
                search.append({"layer": p["layer"], "neuron": p["neuron"], "sense": p["sense"] + 1,
                               "n_senses": p["n_senses"], "cos": float(h.score)})
            yield {"i": t - first, "piece": show_piece(self.tok.decode([ids[t]])), "window": window,
                   "layers": layers, "search": search, "next": nxt, "actual": actual}

    def qa_prompt(self, question):
        """Perguntar: só o formato «Q: pergunta» e «A:», sem exemplos escritos à mão. Devolve (prefixo, texto).

        Tudo o que o modelo responder vem do que aprendeu, nada vem do prompt."""
        return "", f"Q: {' '.join(question.split())}\nA:"

    def reply(self, text, max_new=REPLY_TOKENS, prefix="", short=False):
        """Continuação do texto escolhendo sempre o token mais provável.

        O GPT-2 small não é um assistente: só completa o texto, um token de cada vez. Para no fim do texto
        do modelo e, com short, na primeira mudança de linha (a resposta a uma pergunta)."""
        ids, _ = self._ids(text, prefix)
        with torch.no_grad():
            out = self.model.generate(torch.tensor([ids]), max_new_tokens=SHORT_TOKENS if short else max_new,
                                      do_sample=False, no_repeat_ngram_size=0 if short else 3,
                                      pad_token_id=self.tok.eos_token_id)
        pieces = []
        for t in out[0][len(ids):].tolist():
            raw = self.tok.decode([t])
            if t == self.tok.eos_token_id or (short and "\n" in raw):
                break
            pieces.append(show_piece(raw))
        return pieces

    def _load_detail(self):
        if self._ctx is None:
            self._ctx, self._senses = defaultdict(list), defaultdict(list)
            for c in _read(self._base / "contexts.jsonl"):
                self._ctx[(c["layer"], c["neuron"])].append(c)
            for s in _read(self._base / "senses.jsonl"):
                self._senses[(s["layer"], s["neuron"])].append(s)

    def neuron(self, layer, neuron):
        """Onde um neurónio já acendeu forte (agrupado por sentido) e o que empurra o modelo a dizer."""
        if layer not in self.layers or not 0 <= neuron < self.n_neurons:
            raise ValueError("camada ou neurónio fora do que foi analisado")
        self._load_detail()
        key = (layer, neuron)
        cs = sorted(self._ctx.get(key, []), key=lambda c: c["rank"])
        senses = self._senses.get(key, [])
        sense_of = {r: s["sense"] for s in senses for r in s["ranks"]}
        up, down = self._promotes(layer, neuron, 8)
        return {
            "layer": layer, "neuron": neuron, "max_act": cs[0]["act"] if cs else None,
            "senses": [{"sense": s["sense"] + 1, "size": s["size"], "mean_act": s["mean_act"]} for s in senses],
            "contexts": [{"rank": c["rank"], "act": c["act"], "sense": sense_of.get(c["rank"], 0) + 1,
                          "pieces": [show_piece(self.tok.decode([t])) for t in c["ids"]], "at": c["at"]}
                         for c in cs],
            "promotes": up, "suppresses": down,
        }
