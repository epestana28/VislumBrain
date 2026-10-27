"""Configuração fixa do VislumBrain. Nada aqui depende da máquina ou de quem a usa."""
import os
from pathlib import Path

VERSION = "0.1.0"
CREDITS = "Idealizado por Roberto Pestana, escrito via LLM."

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "corpus"
DATA_DIR = ROOT / "data"
VAULT_DIR = ROOT / "vault"

# Modelo observado. A revisão fica fixa para o Selo ligar cada resultado aos pesos exactos.
MODEL_ID = "openai-community/gpt2"
MODEL_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"

# Embedder das janelas de contexto. Mean pooling feito à mão, sem sentence-transformers.
EMBED_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBED_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBED_DIM = 384

QDRANT_URL = os.environ.get("VISLUMBRAIN_QDRANT_URL", "http://127.0.0.1:6343")
COLLECTION_PREFIX = "vislumbrain_"

# O GPT-2 small tem 1024 de contexto. Blocos curtos chegam e deixam a passagem rápida em CPU.
BLOCK_TOKENS = 256
WINDOW_LEFT = 24
WINDOW_RIGHT = 6

DEFAULT_LAYERS = (3, 7, 11)
DEFAULT_TOPK = 8
# Valores heurísticos, não validados. Ajustar com o corpus à frente.
DEFAULT_MIN_ACT = 0.5
DEFAULT_SENSE_THRESHOLD = 0.95  # escolhido à mão, não validado: a fracção com mais de um sentido varia com o corpus (13% a 58% nas nossas corridas)
DEFAULT_PANEL_PER_LAYER = 14
DEFAULT_MAX_NOTES = 400
