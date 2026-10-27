"""Passo 2: embeddings dos contextos, sentidos por neurónio e carga no Qdrant.

Cada janela de texto é embeddada uma só vez, mesmo que vários neurónios a tenham escolhido.
Um neurónio fica com um vector por sentido (centróide), e é isso que torna a pesquisa polissemântica.
"""
import json
from collections import defaultdict

import numpy as np

from . import config, seal
from .embed import Embedder
from .model import identity, ref_from_label
from .senses import cluster_senses
from .store import Store, pid, point


def build(tag, threshold=config.DEFAULT_SENSE_THRESHOLD, say=print):
    base = config.DATA_DIR / tag
    meta = json.loads((base / "scan_meta.json").read_text(encoding="utf-8"))
    with open(base / "contexts.jsonl", encoding="utf-8") as f:
        ctxs = [json.loads(line) for line in f]

    unique = {}
    for c in ctxs:
        unique.setdefault((c["chunk"], c["pos"]), c["text"])
    keys = list(unique)
    say(f"  index: {len(ctxs)} contextos, {len(keys)} janelas únicas para embeddar")
    vecs = Embedder().encode([unique[k] for k in keys], say=say)
    by_key = {k: vecs[i] for i, k in enumerate(keys)}

    store = Store(tag)
    store.reset()
    groups = defaultdict(list)
    for c in ctxs:
        groups[(c["layer"], c["neuron"])].append(c)

    sense_rows, sense_pts, ctx_pts = [], [], []
    for (layer, neuron), cs in groups.items():
        cs.sort(key=lambda c: c["rank"])
        x = np.stack([by_key[(c["chunk"], c["pos"])] for c in cs])
        labels = cluster_senses(x, threshold)
        n_senses = max(labels) + 1
        for s in range(n_senses):
            idx = [i for i, lab in enumerate(labels) if lab == s]
            centroid = x[idx].mean(0)
            centroid /= np.linalg.norm(centroid) or 1.0
            acts = [cs[i]["act"] for i in idx]
            row = {"layer": layer, "neuron": neuron, "sense": s, "size": len(idx),
                   "mean_act": round(float(np.mean(acts)), 4), "max_act": max(acts),
                   "n_senses": n_senses, "ranks": [cs[i]["rank"] for i in idx]}
            sense_rows.append(row)
            sense_pts.append(point(pid(layer, neuron, s), centroid,
                                   {**{k: v for k, v in row.items() if k != "ranks"},
                                    "example": cs[idx[0]]["text"]}))
        for i, c in enumerate(cs):
            ctx_pts.append(point(pid(layer, neuron, c["rank"]), x[i],
                                 {"layer": layer, "neuron": neuron, "rank": c["rank"],
                                  "act": c["act"], "sense": labels[i], "text": c["text"]}))

    store.upsert(store.sen, sense_pts)
    store.upsert(store.ctx, ctx_pts)
    store.write_meta()
    with open(base / "senses.jsonl", "w", encoding="utf-8") as f:
        for row in sorted(sense_rows, key=lambda r: (r["layer"], r["neuron"], r["sense"])):
            f.write(json.dumps(row) + "\n")

    poly = sum(1 for r in sense_rows if r["sense"] == 1)
    say(f"  index: {len(groups)} neurónios, {len(sense_rows)} sentidos, {poly} neurónios com mais de um sentido")
    s = seal.stamp(tag, "index", params={"threshold": threshold, "senses": len(sense_rows),
                                         "polysemantic_neurons": poly},
                   model=identity(ref_from_label(meta["model"])),
                   artifacts=[base / "senses.jsonl"], qdrant_collections=[store.sen, store.ctx])
    say(f"  selo index: {s[:16]}")
