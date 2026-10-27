# A ciência por trás do VislumBrain, e os seus limites

Esta página é para quem quer conferir as fontes, repetir as medições ou avaliar o que o projecto afirma e o que não afirma. Quem só quer usar a ferramenta não precisa de a ler: o [README](../README.md) e o [guia de sala](GUIA-DE-SALA.md) chegam.

## O que a investigação já mostrou

Isto não é uma ideia nova nem nossa. Vários trabalhos publicados vão no mesmo sentido:

- Allen-Zhu e Li (2024) estudaram, num conjunto controlado de biografias, quando um modelo consegue **ir buscar** um facto para responder a perguntas. Concluíram que isso depende da variedade com que o facto aparece escrito no treino. O que vemos na nossa demonstração é coerente com isto (o texto tem cada facto escrito de uma só maneira), mas não o prova, porque o estudo treinou modelos de raiz e nós só ajustamos um modelo já treinado.
- Berglund et al. (2023) mostraram que um modelo treinado com "A é B" não responde por si só a "B é A" (a "maldição da inversão").
- Gekhman et al. (2024) estudaram o ajuste fino (fine-tuning) com factos novos em modelos grandes e relatam que aprendê-los vem acompanhado de mais respostas inventadas.
- Carlini et al. (2021) mostraram que o GPT-2 consegue reproduzir, palavra por palavra, partes do texto com que foi treinado. É a memorização de que falamos aqui.

Estes trabalhos usam outros modelos e outras condições. Servem para dizer o que é **de esperar**, e não para provar o que se passa na nossa demonstração. Para isso temos só as nossas medições, abaixo.

## O que medimos nós (uma só corrida, não é um resultado científico)

Modelo GPT-2 small (124 milhões de parâmetros). Texto: um artigo em inglês de cerca de 55 KB mais uma caixa de informação com os factos principais, dividido em 47 blocos de 256 tokens. Treino: 20 épocas, taxa de aprendizagem 1e-4, lotes de 4, semente 0, num PC sem placa gráfica. Do texto, 4 blocos (cerca de 1000 tokens) ficaram reservados e nunca foram usados no treino.

| O que medimos | Resultado |
|---|---|
| Inícios de frase do texto cuja palavra seguinte o modelo acerta | 8 em 8 |
| Perguntas sobre o texto respondidas correctamente | 2 em 8 |
| Perda média no treino, na última época (menor é melhor) | 0,15 |
| Perda nos 4 blocos reservados, antes e depois do treino | **piorou**, de 3,46 para 5,62 |

A "perda" mede quanto o modelo se engana a prever a palavra seguinte: menor é melhor. Tecnicamente é a entropia cruzada média por token, em nats. Uma perda de 3,46 equivale a uma perplexidade de cerca de 32, e uma de 5,62 a cerca de 276.

A última linha é a mais importante: o modelo ficou **pior** no texto que não viu. Decorou, e não generalizou. Numa medição anterior, com só 3 épocas e taxa 5e-5, a perda nos mesmos blocos reservados melhorou ligeiramente (de 3,46 para 3,29). Mudámos as duas coisas de uma vez (épocas e taxa), por isso não sabemos qual pesa mais. Os dois resultados são compatíveis com treinar demais (sobreajuste), mas só com uma corrida de cada não o podemos afirmar.

**Limites desta medição, ditos sem rodeios:**

- É **uma** corrida, com **um** texto e **8** perguntas. Não há repetições nem intervalos de confiança.
- As 8 perguntas e os inícios de frase foram escritos por nós a partir do texto, e as respostas foram avaliadas à mão por **um só avaliador**, sem segunda opinião.
- As respostas do modo Pergunta são cortadas aos primeiros 10 tokens. Isto pode cortar uma resposta certa que começasse devagar, e por isso 2 em 8 pode estar por baixo.
- Os blocos reservados são do **mesmo** artigo, e não de um texto independente. Medem se o modelo generaliza dentro do artigo, não fora dele.
- Com outro texto, outro modelo ou outros valores, os números mudam. Corre tu e vê o `finetune_report.json` em `data/ft/`.

## Em que ciência se apoia o desenho

*Esta secção é técnica e serve para quem quer conferir as fontes. Podes saltá-la sem perder o resto.*

O GPT-2 small (Radford et al., 2019) tem 124 milhões de parâmetros, segundo a ficha do modelo na Hugging Face, e 12 camadas. Em cada camada, o bloco chamado MLP tem 3072 neurónios (4 vezes as 768 dimensões do modelo). São 36 864 neurónios de MLP no total. O VislumBrain observa **3 das 12 camadas** (a 3, a 7 e a 11, contando a partir de 0), ou seja 9216 neurónios, e só os neurónios de MLP. Não observa a atenção.

Cada parte do desenho segue uma ideia publicada. A tabela diz qual, e diz também onde o projecto fica aquém dela. As referências completas estão no fim.

| O que o VislumBrain faz | Ideia em que se apoia | Onde fica aquém |
|---|---|---|
| Mostra os textos onde cada neurónio de MLP acende mais | As camadas MLP funcionam como memórias: a entrada de cada neurónio reage a padrões de texto (Geva et al., 2021) | Mostra só os 8 contextos mais fortes, que são o extremo e não o uso típico |
| Diz que palavras o neurónio "promove" e "suprime", e desenha o efeito directo na Saída | Ler o vector de saída do neurónio directamente no vocabulário (Geva et al., 2022), na linha da «logit lens» (nostalgebraist, 2020) | É uma aproximação: ignora a normalização final e as camadas seguintes, e trata o vector de embedding da palavra como a direcção de saída (no GPT-2 a matriz de embeddings é partilhada entre a entrada e a saída) |
| Separa um neurónio em vários "sentidos" | Neurónios polissemânticos e superposição (Elhage et al., 2022) | Agrupa os contextos por semelhança, com um limiar escolhido à mão. Não é uma medida estabelecida na literatura |
| Compara textos por significado | Vectores de frases multilingues (Reimers e Gurevych, 2020) | O modelo usado é da família que segue este método. A qualidade para textos técnicos não foi medida por nós |
| Ablação: põe um neurónio a zero | Testar o que acontece sem ele | Põe a zero em todas as posições e mede só a palavra seguinte. O modelo pode compensar com outras peças (McGrath et al., 2023) |
| Treina com texto próprio e mede em blocos reservados | Prática comum em aprendizagem automática: medir em dados que o modelo não viu | Só 4 blocos do mesmo texto (ver acima) |
| A lição "decorar não é saber" | Allen-Zhu e Li (2024), Berglund et al. (2023), Gekhman et al. (2024), Carlini et al. (2021) | Uma corrida nossa, que não prova nada em geral |

### Onde isto se situa

O VislumBrain **não é a primeira ferramenta** para espreitar o interior de modelos de linguagem, e não pretende substituir as que já existem. O **Neuronpedia** (https://www.neuronpedia.org) é uma plataforma de interpretabilidade aberta e muito robusta, com modelos como o GPT-2 small, pesquisa de características e muito mais. Se o tema te interessar, recomendamos que a conheças. Existem também o Neuroscope (de Neel Nanda, com os 20 exemplos de maior activação de cada neurónio) e o visualizador da OpenAI (2023), com explicações de neurónios escritas por um modelo de linguagem.

O VislumBrain vai no mesmo sentido, mas de forma **simplificada, para formadores e estudantes**. Corre no teu computador (o texto que escreves não sai dele), mostra a animação token a token, e junta a demonstração de treino com texto próprio e a lição de que escrever bem não é o mesmo que saber, com um guião para sala. Não fizemos uma revisão sistemática do que existe nem comparámos a facilidade de uso das ferramentas, por isso **não afirmamos que o projecto seja único** nem que as outras sejam mais difíceis. A diferença que assumimos é a do público a que se dirige.

### Uma limitação de fundo

A investigação mais recente considera que o **neurónio nem sempre é a melhor unidade** para olhar. Como muitos neurónios são polissemânticos, trabalha-se hoje também com "características" (features) obtidas por autoencoders esparsos, que se mostram mais fáceis de interpretar (Bricken et al., 2023; Cunningham et al., 2024). O VislumBrain trabalha com neurónios porque é mais simples de mostrar e de explicar numa sala. É uma escolha didáctica, e não a abordagem mais avançada.

## Limites, ditos sem rodeios

- **É uma prova de conceito.** O GPT-2 small não é o Claude nem o ChatGPT. Mostra mecanismos, não o comportamento dos modelos grandes.
- **Neurónio não é conceito.** O contexto de topo mostra o que o neurónio *detecta*, não o que ele *faz*. A ablação põe o neurónio a zero (e não à sua média, o que pode empurrar o modelo para situações pouco naturais), olha só para o token seguinte e para janelas curtas, e o modelo pode compensar com outras peças (McGrath et al., 2023).
- **Os limiares não estão validados.** O limiar de sentidos (0,95) foi escolhido à mão. A percentagem de neurónios com mais de um sentido muda muito com o corpus: 58% só com os textos de exemplo, 31% com os textos de exemplo e um artigo, e 13% no modelo treinado só com um artigo. Nenhum valor foi confrontado com uma verdade externa, por isso o número de sentidos é indicativo.
- **A pesquisa da vista ao vivo é ruidosa.** Para tokens muito comuns (`The`, `in`) devolve sentidos genéricos.
- **O top-k mostra o extremo.** Os contextos mais fortes não são o uso típico.
- **Neste teste, treinar com um artigo não bastou para responder bem.** Depois do treino, a IA completou bem o início das frases do artigo, mas respondeu certo a poucas perguntas e inventou factos. A perda mede-se em blocos reservados, para se ver se o modelo generaliza ou decora.
- **Qdrant em modo local** é força bruta, sem HNSW. Serve para tudo, menos para o `bench`. O programa regista onde fez o índice. Se depois pesquisares no outro modo (por exemplo, o Docker desligou-se), avisa-te e diz o que fazer, em vez de te dar resultados de outra altura.

## Referências

Conferimos título, autores, local e páginas de cada referência nas páginas oficiais (ACL Anthology, PMLR, arXiv e Transformer Circuits Thread). Para o ICLR, o USENIX, o CHI e o livro de White e Gunstone, confiámos em fontes secundárias. As frases deste README sobre o conteúdo dos artigos resumem o que os autores dizem nos respectivos resumos, e **não lemos todos os artigos na íntegra**. Se fores citar algum, confirma na fonte.

- Allen-Zhu, Z. e Li, Y. (2024). *Physics of Language Models: Part 3.1, Knowledge Storage and Extraction*. ICML 2024, PMLR 235:1067-1077. arXiv:2309.14316.
- Berglund, L. et al. (2023). *The Reversal Curse: LLMs trained on "A is B" fail to learn "B is A"*. arXiv:2309.12288.
- Bricken, T. et al. (2023). *Towards Monosemanticity: Decomposing Language Models With Dictionary Learning*. Transformer Circuits Thread. https://transformer-circuits.pub/2023/monosemantic-features/
- Carlini, N. et al. (2021). *Extracting Training Data from Large Language Models*. USENIX Security 2021. arXiv:2012.07805.
- Cunningham, H., Ewart, A., Riggs, L., Huben, R. e Sharkey, L. (2024). *Sparse Autoencoders Find Highly Interpretable Features in Language Models*. ICLR 2024. arXiv:2309.08600.
- Elhage, N. et al. (2022). *Toy Models of Superposition*. Transformer Circuits Thread. arXiv:2209.10652.
- Gekhman, Z. et al. (2024). *Does Fine-Tuning LLMs on New Knowledge Encourage Hallucinations?* EMNLP 2024, pp. 7765-7784. doi:10.18653/v1/2024.emnlp-main.444.
- Geva, M., Schuster, R., Berant, J. e Levy, O. (2021). *Transformer Feed-Forward Layers Are Key-Value Memories*. EMNLP 2021, pp. 5484-5495. doi:10.18653/v1/2021.emnlp-main.446.
- Geva, M., Caciularu, A., Wang, K. e Goldberg, Y. (2022). *Transformer Feed-Forward Layers Build Predictions by Promoting Concepts in the Vocabulary Space*. EMNLP 2022, pp. 30-45. arXiv:2203.14680.
- Long, D. e Magerko, B. (2020). *What is AI Literacy? Competencies and Design Considerations*. CHI 2020.
- McGrath, T. et al. (2023). *The Hydra Effect: Emergent Self-repair in Language Model Computations*. arXiv:2307.15771.
- nostalgebraist (2020). *interpreting GPT: the logit lens*. LessWrong, 31 de Agosto de 2020. https://www.lesswrong.com/posts/AcKRB8wDpdaN6v6ru
- OpenAI (2023). *Language models can explain neurons in language models*. https://openai.com/index/language-models-can-explain-neurons-in-language-models/
- Radford, A. et al. (2019). *Language Models are Unsupervised Multitask Learners*. OpenAI.
- Reimers, N. e Gurevych, I. (2020). *Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation*. EMNLP 2020, pp. 4512-4525. arXiv:2004.09813.
- White, R. e Gunstone, R. (1992). *Probing Understanding*. Falmer Press.
- Ferramentas (não são artigos): Neuroscope, https://neuroscope.io; Neuronpedia, https://www.neuronpedia.org.
