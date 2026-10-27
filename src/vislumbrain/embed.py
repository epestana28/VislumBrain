"""Embeddings das janelas de contexto: MiniLM multilingue com mean pooling feito à mão."""
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from . import config


class Embedder:
    def __init__(self):
        kw = {"revision": config.EMBED_REVISION}
        self.tok = AutoTokenizer.from_pretrained(config.EMBED_ID, **kw)
        self.model = AutoModel.from_pretrained(config.EMBED_ID, **kw).eval()

    @torch.no_grad()
    def encode(self, texts, batch=64, say=None):
        if not texts:
            return np.zeros((0, config.EMBED_DIM), dtype=np.float32)
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok(texts[i:i + batch], padding=True, truncation=True, max_length=64, return_tensors="pt")
            h = self.model(**enc).last_hidden_state
            m = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
            e = (h * m).sum(1) / m.sum(1).clamp(min=1)
            out.append(torch.nn.functional.normalize(e, dim=1))
            if say and (i // batch) % 40 == 0:
                say(f"  embeddings: {min(i + batch, len(texts))}/{len(texts)}")
        return torch.cat(out).numpy()
