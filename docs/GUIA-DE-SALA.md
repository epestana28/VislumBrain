# Guia de sala: como usar o VislumBrain numa formação

Para formadores, professores e quem apresenta. Há três versões, conforme o tempo que tens. Todas passam pela mesma ideia.

## A ideia

Treinar o modelo com o teu texto mostra duas coisas ao mesmo tempo. A lição está na diferença entre elas.

**1. O modelo absorve o texto.** Depois do treino, completa inícios de frase desse texto com as palavras do original. Parece que "aprendeu".

**2. Isso não é saber.** Faz ao mesmo modelo perguntas sobre os mesmos factos, no modo **Pergunta**. Acerta algumas, falha outras, e inventa datas e nomes com o mesmo ar de certeza. O que ele aprendeu foi a **continuar o texto**, e não a **responder sobre o assunto**.

A lição, dita sem rodeios: **escrever bem não é o mesmo que saber**. Uma IA pode dizer uma frase fluente, confiante e completamente falsa. Quem a lê não consegue distinguir a resposta certa da inventada só pelo tom. Por isso, o que uma IA diz sobre factos deve sempre ser confirmado numa fonte.

## Antes de começar

1. **Instala e abre o painel** (ver o [README](../README.md)). Faz isto em casa, e não à frente da sala.
2. **Testa as tuas frases e perguntas antes.** O GPT-2 small é um modelo pequeno e antigo. Pode escrever coisas falsas, estranhas ou desagradáveis, e a sala vai ver tudo no ecrã. Escolhe só o que já viste e que serve a tua aula.
3. **O modelo percebe bem só inglês.** As frases de exemplo do painel estão em inglês. Prepara as tuas perguntas em inglês, ou explica à sala o que se está a ler.
4. **Aumenta o texto do browser** (Ctrl e +) e usa um ecrã grande. As luzinhas são pequenas.
5. **Comandos:** neste guia estão como no Linux e no macOS (`./vislumbrain`). No Windows, no PowerShell, escreve `.\vislumbrain.cmd` em vez de `./vislumbrain`.

## Versão de 5 minutos, sem treino

Serve quando não tens tempo para treinar nada. Usa só o modelo original.

1. Abre o painel (`./vislumbrain serve --tag base`, no Windows `.\vislumbrain.cmd serve --tag base`) e escreve uma frase simples. Mostra os pedaços de texto a avançar e as luzinhas a acender. Diz: "isto é o interior da IA a ler".
2. Muda para **Pergunta**. Pergunta à sala se o modelo vai acertar uma pergunta de cultura geral e porquê. Faz a pergunta e mostra a resposta.
3. Pergunta: "como sabemos se está certo?" A resposta é a lição: vamos a uma fonte, e não confiamos no tom.

**Cuidado:** não sei o que o modelo responde à tua pergunta. Testa-a antes. Se responder certo por sorte, usa outra, e explica que isso também acontece.

## Versão de 10 minutos, com o modelo treinado já pronto

Prepara em casa: treina o modelo com um texto teu e escreve uma folha com 6 perguntas e as respostas certas, tiradas do texto (ver [como treinar](USO.md#o-corpus-o-que-é-e-para-que-serve)). Abre os dois painéis, `base` e `ft`.

1. **2 min, ver.** No painel `base`, escreve uma frase e mostra as luzinhas a acender.
2. **3 min, completar.** No painel `ft`, modo **Frase**, escreve o início de uma frase do teu texto. O modelo completa-o bem. Pergunta à sala: "então ele já sabe o assunto?" Guarda a pergunta.
3. **3 min, perguntar.** No painel `ft`, modo **Pergunta**, faz 3 perguntas da folha. Antes de mostrares cada resposta, a sala vota "certa", "errada" ou "não sei". Depois confirma na folha.
4. **2 min, concluir.** Volta à pergunta guardada. Pede a cada pessoa uma frase: "como confirmo uma resposta de uma IA?"

## Versão de 40 minutos, a completa

Esta sequência segue a estratégia **Prever, Observar, Explicar** (White e Gunstone, 1992): primeiro a sala diz o que espera, depois vê o que acontece, e por fim explica a diferença. Foi inspirada nas competências de literacia em IA descritas por Long e Magerko (2020), em particular reconhecer os pontos fortes e fracos de uma IA.

**No fim, cada pessoa deve saber:**

1. distinguir uma resposta **fluente** de uma resposta **certa**;
2. dizer o que o treino com texto próprio faz e o que não faz;
3. explicar como se confirma uma resposta de uma IA (numa fonte, e não pelo tom).

**Prepara em casa, nunca ao vivo.** O treino demora cerca de 20 minutos no nosso PC e o passo seguinte também leva o seu tempo (ver [como treinar](USO.md#o-corpus-o-que-é-e-para-que-serve)). Escolhe um texto teu, de uma página ou mais, que o modelo original provavelmente nunca viu (um texto inédito é o ideal). Escreve 6 a 8 perguntas cujas respostas estão **escritas** nesse texto, e anota ao lado a resposta certa, tirada do texto. Esta é a "folha do verificador" e não vai para o programa. Abre dois painéis, em dois terminais:

Linux e macOS:

```bash
./vislumbrain serve --tag base                  # modelo original, http://127.0.0.1:8765
./vislumbrain serve --tag ft --port 8766        # modelo treinado, http://127.0.0.1:8766
```

Windows (um PowerShell para cada):

```powershell
.\vislumbrain.cmd serve --tag base              # modelo original, http://127.0.0.1:8765
.\vislumbrain.cmd serve --tag ft --port 8766    # modelo treinado, http://127.0.0.1:8766
```

**1. Antes do treino (5 min).** No painel `base`, modo **Pergunta**, faz uma das perguntas. Antes de carregar em **Ver**, pergunta à sala: "vai acertar? porquê?" Conta as mãos no ar. Mostra a resposta. Se o texto é teu e inédito, o modelo original não o viu, por isso não tem como saber.

**2. Depois do treino, completar (10 min).** No painel `ft`, modo **Frase**, escreve o início de uma frase do texto. Pergunta: "e agora, vai completar bem?" Mostra o resultado. Pergunta à sala: "então ele já sabe o assunto?" Guarda esta pergunta para o fim.

**3. Depois do treino, responder (10 min).** No painel `ft`, modo **Pergunta**, faz as perguntas da folha. Para cada resposta, a sala vota "certa", "errada" ou "não sei" **antes** de o verificador ler a folha. Regista os votos e o resultado. É provável que apareçam acertos e respostas inventadas ditas com o mesmo tom (na nossa medição, 2 em 8 certas).

**4. Mudar as palavras (5 min).** Faz a mesma pergunta de outra maneira, ou ao contrário (em vez de "qual é a capital de X?", "de que país Y é a capital?"). A investigação sugere que isto pode piorar os resultados (Allen-Zhu e Li, 2024; Berglund et al., 2023). Vejam se na vossa sala acontece, sem prometer o resultado.

**5. Abrir um neurónio (5 min).** Carrega num neurónio que acendeu numa resposta errada e mostra os textos onde ele costuma acender. Ideia a deixar: acender mostra com que textos o neurónio costuma andar, e não prova que "sabe" o facto.

**6. Discussão (5 min).** Volta à pergunta do passo 2: "ele sabe o assunto?" Perguntas para a conversa:

- Em que respostas confiaste só pelo tom?
- Como soubemos qual estava certa? (A resposta é a lição: fomos ver à fonte.)
- Se alguém te mostrasse estas respostas sem a folha do verificador, como as confirmavas?

**Para fechar (2 min).** Pede a cada pessoa que escreva uma frase: "como confirmo uma resposta de uma IA?"

**Cuidado ao apresentar.** Não digas à sala o resultado antes. Não prometas que a demonstração "corre bem": com outro texto os números mudam, e mostrar isso também ensina. Lembra que o GPT-2 small é pequeno e antigo. Modelos maiores costumam errar menos, mas também podem inventar com confiança, por isso a regra de confirmar numa fonte continua a valer.

## O que a sala aprende

A maioria das pessoas só conhece a IA por fora: escreve uma pergunta e lê a resposta. O que se passa no meio fica escondido numa caixa negra. Quem não vê o interior acaba por pensar que a IA é magia, ou que é só "copiar e colar".

O VislumBrain foi criado para a **literacia em IA**: para qualquer pessoa poder ver a IA por outra perspectiva e fazer boas perguntas sobre ela.

Algumas coisas que se aprendem ao experimentar:

- **A IA não lê palavras inteiras.** Lê pedaços, e é isso que aparece no ecrã.
- **Em geral, não há um neurónio para cada ideia.** Muitos neurónios acendem com coisas muito diferentes (Elhage et al., 2022). Alguns são mais "limpos" do que outros.
- **Acender não é o mesmo que ser preciso.** Desligar um neurónio ajuda a ver se ele fazia diferença na palavra seguinte, com os limites que a secção "Limites" explica.
- **O que a IA aprendeu vive nos números dentro dela (os parâmetros).** Podes treinar a IA com um texto (o que tu escolheres) e comparar antes e depois.

Isto não explica o ChatGPT nem o Claude, que são muito maiores. É uma janela didáctica sobre uma IA pequena, onde alguns mecanismos são parecidos e ainda se conseguem ver.

