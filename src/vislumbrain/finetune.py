"""Fine-tuning do GPT-2 small sobre um texto, como prova de conceito.

Com um só artigo o modelo aprende a continuar esse texto, não a responder a perguntas.
A perda mede-se em blocos reservados (nunca treinados) para se ver se generaliza ou só decora.
"""
import json
import random

import torch

from . import config, corpus, seal
from .model import identity, load

FT_DIR = config.DATA_DIR / "ft"
PROBES = 4
PROBE_TOKENS = 8


def _batch(blocks, eos):
    width = max(len(b) for b in blocks)
    ids = torch.full((len(blocks), width), eos)
    mask = torch.zeros((len(blocks), width), dtype=torch.long)
    labels = torch.full((len(blocks), width), -100)
    for i, b in enumerate(blocks):
        ids[i, :len(b)] = torch.tensor(b)
        mask[i, :len(b)] = 1
        labels[i, 1:len(b)] = torch.tensor(b[1:])  # a posição 0 é o EOS de arranque e não conta
    return ids, mask, labels


def _val_loss(model, blocks, eos, batch):
    model.eval()
    total = n = 0.0
    with torch.no_grad():
        for i in range(0, len(blocks), batch):
            ids, mask, labels = _batch(blocks[i:i + batch], eos)
            total += model(input_ids=ids, attention_mask=mask, labels=labels).loss.item()
            n += 1
    return total / max(n, 1)


def _probes(val, tok):
    """Inícios de blocos reservados: o modelo nunca os viu a treinar. Vêm do texto, não do código."""
    return [tok.decode(b[1:1 + PROBE_TOKENS]) for b in val[:PROBES]]


def _complete(model, tok, prompts):
    model.eval()
    out = {}
    for p in prompts:
        enc = tok(p, return_tensors="pt")
        gen = model.generate(**enc, max_new_tokens=20, do_sample=False, pad_token_id=tok.eos_token_id)
        out[p] = tok.decode(gen[0], skip_special_tokens=True)
    return out


def run(files, epochs=3, lr=5e-5, batch=4, seed=0, say=print):
    """Treina com os ficheiros dados (a CLI passa corpus/ inteiro se não se escolher nenhum)."""
    missing = [f for f in files if not f.exists()]
    if missing:
        raise SystemExit(f"faltam ficheiros: {', '.join(f.name for f in missing)}")
    torch.manual_seed(seed)
    rnd = random.Random(seed)
    tok, model = load(None)
    blocks = [ids for _doc, ids in corpus.blocks(files, tok)]
    val = [b for i, b in enumerate(blocks) if i % 10 == 9]
    train = [b for i, b in enumerate(blocks) if i % 10 != 9]
    if not val or not train:
        raise SystemExit(f"texto curto demais: {len(blocks)} blocos. São precisos pelo menos 10 para treinar e reservar alguns")
    say(f"  finetune: {len(train)} blocos de treino, {len(val)} reservados")

    probes = _probes(val, tok)
    before = {"val_loss": _val_loss(model, val, tok.eos_token_id, batch), "samples": _complete(model, tok, probes)}
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    train_losses = []
    for ep in range(epochs):
        model.train()
        rnd.shuffle(train)
        acc = []
        for i in range(0, len(train), batch):
            ids, mask, labels = _batch(train[i:i + batch], tok.eos_token_id)
            loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
            loss.backward()
            opt.step()
            opt.zero_grad()
            acc.append(loss.item())
        train_losses.append(sum(acc) / len(acc))
        say(f"  época {ep + 1}/{epochs}: perda de treino {train_losses[-1]:.3f}")
    after = {"val_loss": _val_loss(model, val, tok.eos_token_id, batch), "samples": _complete(model, tok, probes)}

    out = FT_DIR / "model"
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    report = {"epochs": epochs, "lr": lr, "batch": batch, "seed": seed, "train_loss": train_losses,
              "before": before, "after": after}
    (FT_DIR / "finetune_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    say(f"  perda nos blocos reservados: {before['val_loss']:.3f} -> {after['val_loss']:.3f}")
    for p in probes:
        say(f"  «{p}»\n     antes : {before['samples'][p]!r}\n     depois: {after['samples'][p]!r}")
    s = seal.stamp("ft", "finetune", params={k: report[k] for k in ("epochs", "lr", "batch", "seed")},
                   model=identity(str(out)), corpus_files=files,
                   artifacts=[out, FT_DIR / "finetune_report.json"])
    say(f"  selo finetune: {s[:16]}")
    return report
