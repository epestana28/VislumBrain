# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-PT/1.1.0/).

## [0.1.0] - 2026-10-27

### Adicionado (Windows e documentação)
- Suporte a Windows 10 e 11: `install.ps1` (instalador de uma linha no PowerShell, sem git), atalho `vislumbrain.cmd`, consola forçada a UTF-8 e `os.getuid` protegido. Testado em Windows 11 (instalador, 35 testes, `verify` e painel).
- README reescrito, curto e centrado na literacia em IA, com imagem do painel e instalação para Windows, Linux e macOS.
- Documentação separada em `docs/`: `GUIA-DE-SALA.md` (versões de 5, 10 e 40 minutos), `USO.md` (instalação e comandos) e `CIENCIA.md` (fontes e limites).

### Corrigido
- No modo local do Qdrant deixaram de aparecer avisos em inglês (índices de payload e "mais de 20 000 pontos") na instalação e ao abrir o painel.
- O contentor do Qdrant corre com o utilizador de quem o lança e guarda snapshots e ficheiros temporários na pasta de armazenamento. A pasta `qdrant_storage` é criada antes do `up`, para o Docker não a criar como root.

### Alterado
- `finetune` treina com tudo o que estiver em `corpus/` (como o `run`), já não com um ficheiro escrito no código. O comando que descarregava um artigo foi retirado: o texto de exemplo é o que o utilizador puser em `corpus/`.
- O instalador e o README apontam para o painel (`serve`) como primeiro passo.

### Adicionado
- Fontes conferidas, limites da medição e sugestão de demonstração em sala (Prever, Observar, Explicar), agora em `docs/`.
- Secção do README sobre a lição de literacia da demonstração (decorar não é saber), com as medições e um guião de 10 minutos para formações.
- Modo **Pergunta** no painel: `Q: ...` e `A:` sem exemplos escritos à mão, só o que o modelo aprendeu do corpus.
- As amostras do antes e depois do `finetune` vêm do início de blocos reservados do próprio texto, não do código.
- Pipeline `scan`, `index`, `notes` e `run` sobre o GPT-2 small, com os contextos de topo de cada neurónio.
- Sentidos por neurónio (agrupamento dos contextos) e pesquisa polissemântica no Qdrant, com `bench` de pesquisa aproximada contra exacta.
- Vista ao vivo (`live`) com a pesquisa polissemântica integrada e notas de sessão opcionais.
- Ablação de neurónios, fine-tuning sobre um texto (`finetune`) e comparação base contra ft (`diff`).
- Selo de integridade encadeado e comando `verify`.
- Barreira de corpus: só se lê de `corpus/`, com `--allow-external` explícito.
- Instalador de um comando (`install.sh`) e atalho `./vislumbrain`.
- Qdrant em modo local quando não há servidor, para funcionar sem Docker.
- Painel no browser (`serve`) com animação: o texto avança, os neurónios acendem e, ao escolher um, aparecem os contextos onde dispara. Só escuta em `127.0.0.1`.
- Resposta da IA no fim do painel: continuação do texto gerada pelo GPT-2 small, que entra palavra a palavra.
- Coluna "Saída" no painel: as cinco palavras mais prováveis a seguir, a palavra real da frase e o efeito directo aproximado de cada neurónio na palavra mais provável.
- Notas para Obsidian com as fronteiras dos tokens.
- O índice regista o modo em que foi feito (servidor ou local). `search`, `live` e `bench` recusam, com instrução, um modo ou umas colecções diferentes.
- O `verify` confere cada artefacto pela entrada mais recente que o cobre e falha se faltar um ficheiro de corpus do repositório.

### Segurança
- A barreira de corpus recusa ligações simbólicas que apontem para fora de `corpus/`, e `corpus/private/` só entra se for pedida pelo nome.
- `--tag` e `--topk` são validados.
- `--model` só aceita pastas de pesos dentro do projecto, contadas a partir da raiz dele.

### Alterado
- As dependências têm limite superior (próxima versão maior), para uma versão nova não partir a instalação sem aviso.
- O `diff` mostra `n/d` na activação média quando `base` e `ft` leram corpora diferentes, porque aí a comparação não é válida.
