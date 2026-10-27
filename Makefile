PY ?= .venv/bin/python
VB = PYTHONPATH=src $(PY) -m vislumbrain

.PHONY: up test demo finetune ft verify
up:        ; $(VB) up
test:      ; PYTHONPATH=src $(PY) -m unittest discover -s tests -v
demo:      ; $(VB) run --tag base
finetune:  ; $(VB) finetune
ft:        ; $(VB) run --tag ft --model data/ft/model
verify:    ; $(VB) verify --tag base
