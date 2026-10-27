"""Passo 3: uma nota por neurónio, para abrir no Obsidian (ou em qualquer leitor de Markdown)."""
import json
import shutil
from collections import defaultdict

from . import config, seal
from .model import identity, load, ref_from_label, writes_to
from .util import show_piece


def _line(tok, ids, at):
    parts = [show_piece(tok.decode([t])) for t in ids]
    parts[at] = f"«{parts[at]}»"
    return "·".join(parts)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def write(tag, max_notes=config.DEFAULT_MAX_NOTES, say=print):
    base = config.DATA_DIR / tag
    meta = json.loads((base / "scan_meta.json").read_text(encoding="utf-8"))
    ctx_by, sense_by = defaultdict(list), defaultdict(list)
    for c in _read(base / "contexts.jsonl"):
        ctx_by[(c["layer"], c["neuron"])].append(c)
    for s in _read(base / "senses.jsonl"):
        sense_by[(s["layer"], s["neuron"])].append(s)

    def strength(k):
        return ctx_by[k][0]["act"]

    strongest = sorted(ctx_by, key=lambda k: -strength(k))[:max_notes]
    polysemic = sorted(ctx_by, key=lambda k: (-len(sense_by[k]), -strength(k)))[:100]
    chosen = list(dict.fromkeys(strongest + polysemic))

    ref = ref_from_label(meta["model"])
    tok, model = load(ref)
    out = config.VAULT_DIR / tag / "neurons"
    if out.exists():
        shutil.rmtree(out)  # só a pasta gerada por nós, sempre regenerável
    out.mkdir(parents=True)
    index_seal = (seal.last(tag, "index") or "sem-selo")[:16]
    footer = f"\n---\nSelo do índice: {index_seal} · VislumBrain {config.VERSION}\n{config.CREDITS}\n"

    for key in chosen:
        layer, neuron = key
        cs, senses = sorted(ctx_by[key], key=lambda c: c["rank"]), sense_by[key]
        sense_of = {r: s["sense"] for s in senses for r in s["ranks"]}
        up, down = writes_to(model, tok, layer, neuron)
        fmt = lambda xs: ", ".join(f"`{show_piece(x)}`" for x in xs)
        lines = [
            "---", f"camada: {layer}", f"neuronio: {neuron}", f"tag: {tag}",
            f"act_max: {cs[0]['act']}", f"sentidos: {len(senses)}", "---",
            f"# L{layer}.N{neuron}", "",
            f"- Activação máxima: {cs[0]['act']} · sentidos: {len(senses)}",
            f"- Promove (valor em c_proj): {fmt(up)}",
            f"- Suprime: {fmt(down)}", "",
        ]
        for s in senses:
            lines += [f"## Sentido {s['sense'] + 1} ({s['size']} contextos, act média {s['mean_act']})", ""]
            for c in cs:
                if sense_of.get(c["rank"]) == s["sense"]:
                    lines.append(f"- {c['act']}  `{_line(tok, c['ids'], c['at'])}`")
            lines.append("")
        (out / f"L{layer}.N{neuron}.md").write_text("\n".join(lines) + footer, encoding="utf-8")

    def row(k):
        return f"| [[L{k[0]}.N{k[1]}]] | {len(sense_by[k])} | {strength(k)} |"

    index = ["# Índice", "", f"Tag `{tag}` · modelo `{meta['model']}` · camadas {meta['layers']} · "
             f"{meta['neurons_kept']} neurónios com actividade · {len(chosen)} notas.", "",
             "## Mais polissemânticos", "", "| Neurónio | Sentidos | Act máx |", "|---|---|---|"]
    index += [row(k) for k in polysemic[:30] if k in chosen]
    index += ["", "## Mais fortes", "", "| Neurónio | Sentidos | Act máx |", "|---|---|---|"]
    index += [row(k) for k in strongest[:30]]
    (config.VAULT_DIR / tag / "Indice.md").write_text("\n".join(index) + "\n" + footer, encoding="utf-8")

    say(f"  notes: {len(chosen)} notas em vault/{tag}/neurons")
    s = seal.stamp(tag, "notes", params={"max_notes": max_notes, "notes": len(chosen)},
                   model=identity(ref), artifacts=[out, config.VAULT_DIR / tag / "Indice.md"])
    say(f"  selo notes: {s[:16]}")
