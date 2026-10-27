# Guia de utilização

Tudo o que o VislumBrain faz, com os comandos. **Onde o comando é diferente, mostramos as duas versões: Linux e macOS, e Windows (PowerShell).** Onde só aparece `./vislumbrain`, no Windows escreve `.\vislumbrain.cmd` com os mesmos argumentos.

Conteúdo: [instalar](#instalar-com-mais-pormenor) · [ver o resultado no terminal](#o-que-vais-ver) · [pesquisar e desligar neurónios](#pergunta-o-que-quiseres) · [o corpus e treinar](#o-corpus-o-que-é-e-para-que-serve) · [o painel](#vê-num-painel-com-animação) · [palavras novas](#palavras-novas) · [comandos](#comandos-principais) · [como funciona](#como-funciona) · [privacidade](#privacidade-e-corpus)

## Instalar, com mais pormenor

Precisas de **Python 3.11 ou mais recente**, de internet e de uns 3 GB livres no disco. O instalador faz tudo sozinho: cria uma pasta `VislumBrain`, um ambiente isolado dentro dela (`.venv`), instala as bibliotecas, descarrega os modelos e corre a demonstração. Não usa administrador nem `sudo`, e não mexe no resto do sistema. O painel precisa de memória: num Windows 11 com 2 núcleos e 4 GB funcionou, mas cada frase demorou cerca de 75 segundos, contra uns 2 segundos num PC com 16 núcleos.

**Windows 10 ou 11 (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/epestana28/VislumBrain/main/install.ps1 | iex
```

Se não tens Python, instala-o com `winget install Python.Python.3.12` (ou em python.org, a marcar "Add python.exe to PATH"), abre um PowerShell novo e corre a linha outra vez. Não precisas de Docker nem de git. O Qdrant usa o modo local.

**Linux e macOS:**

```bash
curl -fsSL https://raw.githubusercontent.com/epestana28/VislumBrain/main/install.sh | bash
```

O instalador para Linux e macOS precisa também de `git`. No macOS deve funcionar, mas só foi testado em Linux.

**Preferes ler antes de correr?** É uma boa prática, porque estas linhas correm código descarregado da internet. Abre o endereço no browser (`install.ps1` ou `install.sh`, na página do projecto) e lê. Em Linux ou macOS também podes fazer:

```bash
wget -O install.sh https://raw.githubusercontent.com/epestana28/VislumBrain/main/install.sh
less install.sh
bash install.sh
```

**Opções.** Para instalar sem a demonstração: no Linux acrescenta `--no-demo` (`... | bash -s -- --no-demo`); no Windows define antes `$env:VISLUMBRAIN_NO_DEMO = "1"`. Já tens a pasta do projecto? Corre `bash install.sh` (ou `.\install.ps1`) dentro dela.

**Se algo falhar:**

- *"preciso de Python 3.11 ou superior"*: instala-o como acima e abre um terminal novo.
- *Falta de espaço ou internet a meio*: o instalador pode repetir-se sem risco. Corre-o outra vez.
- *Outra coisa*: copia a mensagem de erro para a página de [Issues](https://github.com/epestana28/VislumBrain/issues), com o teu sistema e a versão do Python.

**Docker (opcional).** O Qdrant corre em modo local, sem Docker. Se tiveres Docker, `./vislumbrain up` (Windows: `.\vislumbrain.cmd up`) liga um servidor Qdrant, que é mais rápido e permite o comando `bench`. No Windows isto não foi testado.

## O que vais ver

Para cada pedaço da frase, o programa mostra quais neurónios acenderam. Isto mostra o **formato** da saída. Os valores aqui são ilustrativos: os teus dependem do corpus e do modelo.

```
▁bank
    [[L3.N43]]  act 1.92 (54% do máx)  sentido 1/2 (cos 0.81) «The bank approved the loan after reviewing the»
    pesquisa 0.78  [[L7.N2457]] sentido 1/3
```

Como se lê:

- `▁bank` é o pedaço de texto que a IA acabou de ler.
- `L3.N43` é o nome do neurónio: **L**ayer (andar) 3, **N**eurónio número 43.
- `act` é a força da luzinha. Quanto maior, mais acendeu.
- `(54% do máx)` diz quanto isto é forte para esse neurónio, comparado com o máximo que ele já mostrou.
- `sentido 1/2` quer dizer que este neurónio tem 2 maneiras de ser usado e que agora está na primeira.
- A frase entre aspas é um texto onde esse neurónio já tinha acendido forte. Aqui são frases sobre bancos e empréstimos.
- As linhas `pesquisa` mostram outros neurónios que já acenderam com textos parecidos com este.

Cuidado com uma coisa: um neurónio acender ao lado de uma frase não quer dizer que ele "sabe" o que é um banco. Mostra só com que textos costuma andar.

## Pergunta o que quiseres

Escreve uma ideia e o programa diz que neurónios costumam acender com ela:

```bash
./vislumbrain search --tag base "money deposited in a bank account"
```

Para ver se um neurónio muda o resultado, desliga-o (põe-no a zero) e vê o que muda:

```bash
./vislumbrain ablate 3 584
```

Para confirmar que ninguém mexeu nos resultados (é o Selo, explicado abaixo):

```bash
./vislumbrain verify --tag base
```

## O corpus: o que é e para que serve

O corpus é o texto que o programa lê. Tudo o que vês, os neurónios a acender, os contextos e a pesquisa, vem dele. Sem corpus não há nada para mostrar.

O repositório traz textos curtos de exemplo em `corpus/sample/`. Para uma demonstração mais convincente, põe lá o teu próprio texto: um artigo, um manual, notas. Fica só no teu computador e nunca vai para o repositório.

O objectivo é **demonstrar que podes treinar o GPT-2 small com texto teu** e ver o que muda lá dentro. O caminho é sempre o mesmo: **pões o texto em `corpus/` e treinas**.

Isto **não é automático** e demora. Faz por esta ordem:

**Linux e macOS:**

```bash
cp o-meu-texto.txt corpus/                         # 1. mete o teu texto (.txt ou .md) em corpus/
./vislumbrain finetune --epochs 20 --lr 1e-4       # 2. treina com tudo o que está em corpus/
./vislumbrain run --tag ft --model data/ft/model   # 3. prepara os dados do modelo treinado
./vislumbrain serve --tag ft                       # 4. abre o painel com o modelo treinado
./vislumbrain diff                                 # 5. (opcional) o que mudou face ao original
```

**Windows (PowerShell):**

```powershell
Copy-Item .\o-meu-texto.txt corpus\                       # 1. mete o teu texto (.txt ou .md) em corpus\
.\vislumbrain.cmd finetune --epochs 20 --lr 1e-4          # 2. treina com tudo o que está em corpus\
.\vislumbrain.cmd run --tag ft --model data/ft/model      # 3. prepara os dados do modelo treinado
.\vislumbrain.cmd serve --tag ft                          # 4. abre o painel com o modelo treinado
.\vislumbrain.cmd diff                                    # 5. (opcional) o que mudou face ao original
```

O `finetune` e o `run` leem **todos** os ficheiros de `corpus/`. Se quiseres treinar só com um, indica-o: `./vislumbrain finetune --corpus corpus/o-meu-texto.txt` (Windows: `.\vislumbrain.cmd finetune --corpus corpus/o-meu-texto.txt`). Usa o mesmo texto nos passos 2 e 3, para o painel mostrar o que o modelo realmente aprendeu.

O passo 2 é o mais demorado: num PC com 16 núcleos e sem placa gráfica, 20 épocas sobre um texto de cerca de 50 KB levaram cerca de 20 minutos. O passo 3 volta a ler o texto todo e também demora.

Cuidado com o que isto prova: lê a secção seguinte antes de mostrares isto a alguém.

Nenhuma resposta está escrita no código. O que o modelo diz vem do que ele aprendeu: primeiro, no treino original que a OpenAI fez com texto da internet; depois, se o treinaste, do teu texto.

## Acrescenta o teu texto e faz a pesquisa crescer

A IA só mostra os contextos dos textos que lhe deste a ler. Quanto mais texto puseres, mais contextos a pesquisa encontra. Tu escolhes o texto.

**1. Põe os teus ficheiros em `corpus/`.** Servem ficheiros `.txt` e `.md`. Podes criar uma pasta tua:

```bash
mkdir corpus/meu
cp os-meus-textos/*.txt corpus/meu/
```

No Windows (PowerShell):

```powershell
mkdir corpus\meu
Copy-Item .\os-meus-textos\*.txt corpus\meu\
```

**2. Lê tudo de novo.** Isto refaz as notas e a pesquisa já com o texto novo. O programa não junta aos poucos: lê tudo outra vez, por isso com muito texto demora mais.

```bash
./vislumbrain run --tag base
```

Para guardar o teu conjunto à parte, sem mexer no `base`, dá-lhe outro nome e diz só que pasta ler:

```bash
./vislumbrain run --tag meu --corpus corpus/meu
./vislumbrain search --tag meu "a minha pergunta"
```

No Windows, o mesmo com `.\vislumbrain.cmd` (e `run --tag base` do passo 2 também).

**3. Pesquisa.** A pesquisa passa a encontrar contextos dos teus textos, e as notas novas aparecem em `vault/<nome>`.

Texto que não queres misturar com o resto vai para `corpus/private/`. O programa só o lê se o pedires de propósito, com `--corpus corpus/private`.

## Acompanha o cérebro enquanto ele lê

O `live` mostra as luzinhas de qualquer texto, não só de uma frase. Escreve a frase com `--text`, ou passa-lhe vários textos de uma vez, um por linha:

**Linux e macOS:**

```bash
./vislumbrain live --tag base < frases.txt
```

**Windows (PowerShell).** O PowerShell não aceita `<`, e passar texto por `|` estraga os acentos. Escreve a frase com `--text`, que é o mais simples:

```powershell
.\vislumbrain.cmd live --tag base --text "The bank near the river opened a new account."
```

Cada linha de `frases.txt` é uma sessão. Com `--note`, cada sessão fica guardada em `vault/base/sessoes/` e podes abri-la no Obsidian para comparar o que acendeu em dias diferentes (em Linux: `./vislumbrain live --tag base --note < frases.txt`; no Windows junta `--note` ao comando com `--text`).

O `live` mostra o que acontece dentro do **GPT-2 small** ao ler esse texto. Não mostra o interior de outra IA, mesmo que o texto tenha sido escrito por ela.

## Vê num painel, com animação

Quem prefere ver a ler o terminal pode abrir o painel no browser:

```bash
./vislumbrain serve --tag base          # Linux, macOS
```

```powershell
.\vislumbrain.cmd serve --tag base      # Windows (PowerShell)
```

Depois abre http://127.0.0.1:8765. O texto avança token a token e os neurónios acendem a amarelo, camada a camada. Carrega num deles e vês à direita os textos onde ele já acendeu forte, com a palavra que o fez acender destacada, agrupados por sentido.

Podes pausar, andar token a token, mudar a velocidade ou escrever a tua frase. O painel só fala com este computador (`127.0.0.1`) e recusa pedidos vindos de outras páginas.

À direita está a **Saída**: as cinco palavras que o modelo diria a seguir, com a probabilidade real de cada uma, e a palavra que a frase realmente tem a seguir.

**Frase ou Pergunta.** No topo da caixa de texto escolhes o modo. Em **Frase**, a IA continua o que escreveste. Em **Pergunta**, o painel escreve `Q: a tua pergunta` e `A:` e deixa o modelo completar. Não há exemplos nem respostas escritas no programa: nenhuma resposta está escrita no programa, tudo o que sai vem do que o modelo aprendeu (no treino original e, se o treinaste, no teu texto). Mostra o que o treino com texto próprio faz e o que não faz. Um GPT-2 small treinado só com texto corrido acerta algumas perguntas, falha outras e inventa datas, e o painel não esconde isso.

As linhas laranja ligam o token que está a ser lido a cada neurónio que acendeu, com mais espessura quando acende mais forte. As linhas verdes e vermelhas ligam os neurónios à Saída: verde empurra o modelo para a palavra mais provável, vermelho afasta-o. É o efeito directo do neurónio e é uma aproximação, porque ignora a normalização final e o trabalho das camadas seguintes.

No fim da frase aparece **A resposta da IA**: a continuação que o GPT-2 small escreve, palavra a palavra. Ele não é um assistente, só completa o texto escolhendo sempre a palavra mais provável, por isso a continuação pode ser estranha ou repetitiva.

Os pesos entre neurónios de camadas diferentes não são desenhados, porque não os medimos. Desenhá-los seria inventar.

## Palavras novas

| Palavra | Quer dizer |
|---|---|
| **IA** | um programa que aprendeu a lidar com texto lendo muitos exemplos |
| **Neurónio** | uma pequena peça da IA que acende com certos textos |
| **Token** | um pedaço de texto que a IA lê. Uma palavra pode ser um ou vários pedaços |
| **Contexto** | o texto à volta de uma palavra, que lhe dá o sentido |
| **Polissemântico** | diz-se de um neurónio que acende em situações sem relação entre si, como um interruptor que serve para duas luzes diferentes. É o termo usado na investigação (Elhage et al., 2022). Nas palavras, `bank` é um caso de homonímia (dois significados sem relação), e não de polissemia no sentido da linguística |
| **Ablação** | desligar um neurónio para ver se ele fazia falta |
| **Selo** | uma marca que prova que os resultados não foram alterados |

## Comandos principais

| Comando | O que faz |
|---|---|
| `run --tag base` | faz tudo de seguida: lê, organiza, cria as notas e põe o Selo. Os passos soltos são `scan`, `index` e `notes` |
| `live --text "..."` | a cada pedaço, que neurónios acendem, com a pesquisa ao lado. `--note` guarda a sessão |
| `search "texto"` | do texto até ao neurónio e sentido mais parecidos. `--exact` usa força bruta |
| `bench` | compara a pesquisa rápida com a exacta (precisa do Qdrant em Docker) |
| `ablate CAMADA NEURÓNIO` | desliga o neurónio e mede o efeito |
| `finetune` | treina a IA com o texto que puseres em `corpus/` |
| `run --tag ft --model data/ft/model` e `diff` | observa a IA treinada e compara com a original |
| `verify` | confere o Selo |
| `up` e `down` | liga ou desliga o Qdrant do projecto |

## Ver as notas no Obsidian

O programa escreve uma nota por neurónio em `vault/base/neurons`. Abre a pasta `vault/base` como cofre no Obsidian, ou lê as notas em qualquer editor. Cada nota mostra os textos onde o neurónio acende mais, com as fronteiras dos tokens (`▁the·▁capital·«▁city»·,`), os tokens que promove e suprime, e os sentidos em que os contextos se agrupam.

## Como funciona

```
corpus/ → GPT-2 small → hook na saída da função de activação dos MLP das camadas observadas
          └→ por neurónio, os contextos onde mais dispara (top-k)
             └→ cada janela de texto é embeddada uma só vez
                └→ os contextos de um neurónio são agrupados em sentidos
                   └→ Qdrant: um vector por sentido  → pesquisa polissemântica
                   └→ vault/: uma nota por neurónio  → abrir no Obsidian
                                                  └→ Selo
```

Um neurónio não tem um vector, tem um por sentido. Pesquisar um texto encontra o sentido mais próximo, e o neurónio vem com ele.

## O Selo

No fim de cada etapa, o Selo grava em `data/<tag>/seal.json` os hashes do corpus e dos resultados, o modelo e a sua revisão, os parâmetros e as versões do software. Cada entrada inclui o hash da anterior, por isso mexer em qualquer coisa parte a cadeia. O comando `verify` volta a calcular os hashes dos ficheiros e confere a cadeia, e diz onde falha. Não reconfere o que está dentro do Qdrant nem os pesos do modelo.

O Selo prova **integridade e proveniência**: que o resultado não foi alterado e de onde veio. Não prova autoria, porque não há chave de assinatura. Não tem caminhos absolutos nem o nome do utilizador ou da máquina. Tem os créditos e as versões do software.

## Privacidade e corpus

- **Nada teu entra sem tu decidires.** O corpus só é lido de `corpus/`. Qualquer caminho fora é recusado, a menos que passes `--allow-external`.
- **Texto privado.** Põe-no em `corpus/private/`: não entra por omissão e está no `.gitignore`.
- **`data/` e `vault/` guardam excertos do texto lido.** Estão no `.gitignore` e não devem ir para o git.
- O corpus de exemplo (`corpus/sample/`) é sintético, escrito para este projecto.

## Desinstalar

Se usaste o Docker, corre `./vislumbrain down` antes (Windows: `.\vislumbrain.cmd down`). Depois apaga a pasta e os modelos descarregados.

**Linux e macOS:**

```bash
rm -rf VislumBrain ~/.cache/huggingface
```

A pasta `qdrant_storage` é criada com o teu utilizador. Se a tiveres de uma versão anterior, pode ter ficado do root e precisar de `sudo` para ser apagada.

**Windows (PowerShell):**

```powershell
Remove-Item -Recurse -Force VislumBrain, $HOME\.cache\huggingface
```

Também podes apagar a pasta `VislumBrain` no Explorador de Ficheiros.

## Estrutura

```
src/vislumbrain/   o código (config, scan, indexer, notes, live, search, ablate, finetune, diff, seal)
corpus/sample/     texto de exemplo, sintético
tests/             testes (make test)
install.sh         instalador de um comando (Linux, macOS)
install.ps1        instalador de um comando (Windows)
vislumbrain        atalho: ./vislumbrain <comando> (Linux, macOS)
vislumbrain.cmd    atalho: .\vislumbrain.cmd <comando> (Windows)
docs/              guias e ciência
```

## Licenças e atribuições

- O código deste projecto tem licença MIT (ver `LICENSE`).
- **GPT-2 small** (`openai-community/gpt2`): licença MIT. O projecto fixa a revisão `607a30d7`.
- **Embedder** (`paraphrase-multilingual-MiniLM-L12-v2`) e **Qdrant**: ver as licenças nos respectivos repositórios.
