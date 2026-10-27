"""Carregar o GPT-2 e observar (ou desligar) neurónios das camadas MLP.

Na MLP do GPT-2, c_proj recebe h = GELU(c_fc(x)). É esse h, com um valor por neurónio,
que se observa: um pre-hook em c_proj apanha-o sem alterar o cálculo.
"""
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import config
from .util import relpath, sha256_file


def resolve_model(ref):
    """Caminho de pesos locais, sempre dentro do projecto. Relativo, conta a partir da raiz do projecto,
    para o mesmo comando dar o mesmo resultado venha de onde vier. Fora do projecto, o Selo e as notas
    não o conseguiriam voltar a encontrar."""
    if not ref:
        return None
    p = Path(ref)
    p = (p if p.is_absolute() else config.ROOT / p).resolve()
    if not p.is_relative_to(config.ROOT.resolve()) or not p.is_dir():
        raise ValueError(f"--model tem de ser uma pasta de pesos dentro do projecto (por exemplo data/ft/model), não {ref!r}")
    return str(p)


def load(ref=None):
    """ref vazio carrega o GPT-2 oficial na revisão fixa. Um caminho existente carrega pesos locais."""
    ref = ref or config.MODEL_ID
    kw = {} if Path(ref).exists() else {"revision": config.MODEL_REVISION}
    tok = AutoTokenizer.from_pretrained(ref, **kw)
    tok.model_max_length = int(1e9)  # blocos longos são partidos por nós, sem avisos inúteis
    model = AutoModelForCausalLM.from_pretrained(ref, **kw).eval()
    return tok, model


def identity(ref=None):
    """Quem é o modelo, para o Selo."""
    if ref and Path(ref).exists():
        w = Path(ref) / "model.safetensors"
        return {"local": relpath(ref), "weights_sha256": sha256_file(w) if w.exists() else None}
    return {"id": config.MODEL_ID, "revision": config.MODEL_REVISION}


def label(ref=None):
    return relpath(ref) if ref and Path(ref).exists() else config.MODEL_ID


def ref_from_label(lbl):
    """Inverso de label(): o que o scan gravou em scan_meta.json volta a ser uma referência carregável."""
    return None if lbl == config.MODEL_ID else str(config.ROOT / lbl)


def n_neurons(model):
    return model.config.n_inner or 4 * model.config.n_embd


class Recorder:
    """Guarda h (batch, tokens, neurónios) das camadas pedidas durante o forward."""

    def __init__(self, model, layers):
        self.model, self.layers = model, layers
        self.acts, self._handles = {}, []

    def __enter__(self):
        for layer in self.layers:
            proj = self.model.transformer.h[layer].mlp.c_proj
            self._handles.append(proj.register_forward_pre_hook(self._make(layer)))
        return self

    def _make(self, layer):
        def hook(_module, args):
            self.acts[layer] = args[0].detach()
        return hook

    def __exit__(self, *exc):
        for h in self._handles:
            h.remove()


class Ablate:
    """Põe um neurónio a zero em todas as posições."""

    def __init__(self, model, layer, neuron):
        self.proj = model.transformer.h[layer].mlp.c_proj
        self.neuron = neuron

    def __enter__(self):
        def hook(_module, args):
            x = args[0].clone()
            x[..., self.neuron] = 0
            return (x,)
        self._handle = self.proj.register_forward_pre_hook(hook)
        return self

    def __exit__(self, *exc):
        self._handle.remove()


def writes_to(model, tok, layer, neuron, k=8):
    """Tokens que o valor do neurónio (linha de c_proj) promove e suprime, lendo-o directamente no vocabulário."""
    w = model.transformer.h[layer].mlp.c_proj.weight[neuron].detach()
    logits = model.transformer.wte.weight.detach() @ w
    up = [tok.decode([i]) for i in logits.topk(k).indices.tolist()]
    down = [tok.decode([i]) for i in (-logits).topk(k).indices.tolist()]
    return up, down
