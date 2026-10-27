"""O que mudou no modelo depois do fine-tuning: pesos de cada neurónio e activação média no corpus."""
import json

import numpy as np

from . import config, seal
from .finetune import FT_DIR
from .model import identity, load
from .util import show_piece


def run(layers=config.DEFAULT_LAYERS, top=20, say=print):
    _, base = load(None)
    _, ft = load(str(FT_DIR / "model"))
    rows = []
    for layer in layers:
        mb, mf = base.transformer.h[layer].mlp, ft.transformer.h[layer].mlp
        # c_fc.weight é (768, N): a coluna n é a chave. c_proj.weight é (N, 768): a linha n é o valor.
        d_key = ((mf.c_fc.weight - mb.c_fc.weight).norm(dim=0) / mb.c_fc.weight.norm(dim=0)).detach()
        d_val = ((mf.c_proj.weight - mb.c_proj.weight).norm(dim=1) / mb.c_proj.weight.norm(dim=1)).detach()
        score = d_key + d_val
        for n in score.topk(top).indices.tolist():
            rows.append((float(score[n]), layer, n, float(d_key[n]), float(d_val[n])))
    rows = sorted(rows, reverse=True)[:top]

    stats = {}
    for tag in ("base", "ft"):
        p = config.DATA_DIR / tag / "stats.npz"
        if p.exists():
            z = np.load(p)
            stats[tag] = {int(l): z["mean"][i] for i, l in enumerate(z["layers"])}
    same_corpus = seal.corpus_paths("base") == seal.corpus_paths("ft")
    if not same_corpus:
        say("aviso: base e ft leram corpora diferentes, por isso a variação da activação média não é comparável (n/d).")
    ft_top = {}
    cp = config.DATA_DIR / "ft" / "contexts.jsonl"
    if cp.exists():
        with open(cp, encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                if c["rank"] == 0:
                    ft_top[(c["layer"], c["neuron"])] = c["text"].replace("\n", " ")[:70]

    out = ["# Diferenças base e ft", "",
           "Neurónios cujos pesos mais mudaram com o fine-tuning (variação relativa da chave e do valor).",
           "" if same_corpus else "A coluna da activação média está em n/d: base e ft leram corpora diferentes.", "",
           "| Neurónio | Δ chave | Δ valor | Δ act média | Contexto de topo (ft) |", "|---|---|---|---|---|"]
    say("neurónios cujos pesos mais mudaram (Δ relativo da chave, do valor, e da activação média no corpus):")
    for _score, layer, n, dk, dv in rows:
        da = ""
        if same_corpus and "base" in stats and "ft" in stats and layer in stats["base"] and layer in stats["ft"]:
            da = f"{float(stats['ft'][layer][n] - stats['base'][layer][n]):+.3f}"
        ctx = ft_top.get((layer, n), "")
        say(f"  L{layer}.N{n}  Δchave {dk:.4f}  Δvalor {dv:.4f}  Δact {da or 'n/d'}  {ctx}")
        out.append(f"| [[L{layer}.N{n}]] | {dk:.4f} | {dv:.4f} | {da or 'n/d'} | {ctx} |")
    path = config.VAULT_DIR / "ft" / "Diferencas.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    seal.stamp("ft", "diff", params={"layers": list(layers), "top": top},
               model=identity(str(FT_DIR / "model")), artifacts=[path])
    return rows
