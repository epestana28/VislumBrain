"""Ablação: o neurónio só disparar não prova que é usado. Desligado, a previsão piora?"""
import json
from collections import defaultdict

import torch

from . import config
from .model import Ablate, load, ref_from_label


def _jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def run(tag, layer, neuron, say=print):
    base = config.DATA_DIR / tag
    meta = json.loads((base / "scan_meta.json").read_text(encoding="utf-8"))
    ctxs = [c for c in _jsonl(base / "contexts.jsonl") if c["layer"] == layer and c["neuron"] == neuron]
    if not ctxs:
        say(f"L{layer}.N{neuron} não tem contextos nesta tag")
        return None
    sense_of = {r: s["sense"] for s in _jsonl(base / "senses.jsonl")
                if s["layer"] == layer and s["neuron"] == neuron for r in s["ranks"]}
    tok, model = load(ref_from_label(meta["model"]))

    deltas = defaultdict(list)
    with torch.no_grad():
        for c in ctxs:
            ids = torch.tensor([[tok.eos_token_id] + c["ids"]])
            at = c["at"] + 1
            if at + 1 >= ids.shape[1]:
                continue
            target = ids[0, at + 1]

            def nll():
                return -torch.log_softmax(model(ids).logits[0, at], -1)[target].item()

            normal = nll()
            with Ablate(model, layer, neuron):
                ablated = nll()
            deltas[sense_of.get(c["rank"], 0)].append(ablated - normal)

    say(f"L{layer}.N{neuron}: variação da perda no token seguinte ao activado (positivo = o neurónio ajudava)")
    allv = []
    for s in sorted(deltas):
        v = deltas[s]
        allv += v
        say(f"  sentido {s + 1}: {sum(v) / len(v):+.4f} em {len(v)} contextos")
    if allv:
        say(f"  total   : {sum(allv) / len(allv):+.4f} em {len(allv)} contextos")
    return deltas
