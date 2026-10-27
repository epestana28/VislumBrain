"""Vista ao vivo: para cada token que entra, que neurónios disparam e em que sentido estão a ser usados."""
from datetime import datetime, timezone

from . import config
from .engine import Engine


def run(tag, texts, top=5, note=False, say=print):
    engine = Engine(tag)

    session = None
    if note:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        session = config.VAULT_DIR / tag / "sessoes" / f"{stamp}.md"
        session.parent.mkdir(parents=True, exist_ok=True)
        session.write_text(f"# Sessão {stamp}\n\n", encoding="utf-8")

    def emit(line):
        say(line)
        if session:
            with open(session, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    for text in texts:
        for step in engine.steps(text, per_layer=top, max_lit=top):
            emit(f"\n`{step['piece']}`" if session else f"\n{step['piece']}")
            lit = sorted(((n["score"], lay["layer"], n) for lay in step["layers"] for n in lay["neurons"] if n["lit"]),
                         key=lambda x: -x[0])[:top]
            for score, layer, n in lit:
                p = n["sense"]
                what = (f"sentido {p['sense']}/{p['n_senses']} (cos {p['cos']:.2f}) «{p['example'][:48].replace(chr(10), ' ')}»"
                        if p else "sem sentido registado")
                emit(f"    [[L{layer}.N{n['neuron']}]]  act {n['act']:.2f} ({score * 100:.0f}% do máx)  {what}")
            # pesquisa polissemântica integrada: os sentidos de todo o índice mais próximos deste contexto
            for h in step["search"]:
                emit(f"    pesquisa {h['cos']:.2f}  [[L{h['layer']}.N{h['neuron']}]] sentido {h['sense']}/{h['n_senses']}")
