"""Passo 1: passa o corpus pelo modelo e guarda, por neurónio, os contextos onde mais dispara."""
import json
import time

import numpy as np
import torch

from . import config, corpus, seal
from .model import Recorder, identity, label, load, n_neurons


def merge_topk(vals, pos, chunk, new_vals, new_pos, chunk_id, k):
    """Junta candidatos novos ao top-k corrente.

    vals, pos, chunk: (N, K). new_vals, new_pos: (k_novo, N), como sai de topk(dim=0).
    """
    cat_v = torch.cat([vals, new_vals.T], dim=1)
    cat_p = torch.cat([pos, new_pos.T], dim=1)
    cat_c = torch.cat([chunk, torch.full_like(new_pos.T, chunk_id)], dim=1)
    top_v, top_i = cat_v.topk(k, dim=1)
    return top_v, cat_p.gather(1, top_i), cat_c.gather(1, top_i)


def scan(tag, files, model_ref=None, layers=config.DEFAULT_LAYERS, topk=config.DEFAULT_TOPK,
         min_act=config.DEFAULT_MIN_ACT, say=print):
    t0 = time.time()
    tok, model = load(model_ref)
    blocks = list(corpus.blocks(files, tok))
    n = n_neurons(model)
    nl = len(layers)
    vals = torch.full((nl, n, topk), float("-inf"))
    pos = torch.zeros((nl, n, topk), dtype=torch.long)
    chk = torch.full((nl, n, topk), -1, dtype=torch.long)
    s1, s2 = torch.zeros(nl, n), torch.zeros(nl, n)
    count = 0

    with torch.no_grad(), Recorder(model, layers) as rec:
        for cid, (_doc, ids) in enumerate(blocks):
            model(torch.tensor([ids]))
            for li, layer in enumerate(layers):
                a = rec.acts[layer][0, 1:, :]
                v, p = a.topk(min(topk, a.shape[0]), dim=0)
                vals[li], pos[li], chk[li] = merge_topk(vals[li], pos[li], chk[li], v, p + 1, cid, topk)
                s1[li] += a.sum(0)
                s2[li] += (a * a).sum(0)
            count += len(ids) - 1
            if (cid + 1) % 20 == 0 or cid + 1 == len(blocks):
                say(f"  scan: {cid + 1}/{len(blocks)} blocos")

    if count == 0:
        raise SystemExit("o corpus não deu nenhum bloco: cada ficheiro precisa de pelo menos 16 tokens")
    mean = s1 / count
    std = (s2 / count - mean * mean).clamp(min=0).sqrt()
    out = config.DATA_DIR / tag
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "stats.npz", layers=np.array(layers), mean=mean.numpy(),
                        std=std.numpy(), max=vals[:, :, 0].numpy())

    v_np, p_np, c_np = vals.numpy(), pos.numpy(), chk.numpy()
    kept = n_ctx = 0
    with open(out / "contexts.jsonl", "w", encoding="utf-8") as f:
        for li, layer in enumerate(layers):
            for nr in range(n):
                if v_np[li, nr, 0] < min_act:
                    continue
                kept += 1
                for r in range(topk):
                    act = float(v_np[li, nr, r])
                    if act < min_act:
                        break
                    cid, p = int(c_np[li, nr, r]), int(p_np[li, nr, r])
                    ids = blocks[cid][1]
                    lo = max(1, p - config.WINDOW_LEFT)
                    win = ids[lo:min(len(ids), p + 1 + config.WINDOW_RIGHT)]
                    f.write(json.dumps({"layer": layer, "neuron": nr, "rank": r, "act": round(act, 4),
                                        "chunk": cid, "pos": p, "ids": win, "at": p - lo,
                                        "text": tok.decode(win)}, ensure_ascii=False) + "\n")
                    n_ctx += 1

    meta = {"model": label(model_ref), "layers": list(layers), "topk": topk, "min_act": min_act,
            "n_neurons": n, "tokens_scanned": count, "blocks": len(blocks),
            "neurons_kept": kept, "contexts": n_ctx}
    (out / "scan_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    say(f"  scan: {kept} neurónios com actividade, {n_ctx} contextos, {count} tokens, {time.time() - t0:.0f}s")
    s = seal.stamp(tag, "scan", params=meta, model=identity(model_ref), corpus_files=files,
                   artifacts=[out / "contexts.jsonl", out / "stats.npz", out / "scan_meta.json"])
    say(f"  selo scan: {s[:16]}")
    return meta
