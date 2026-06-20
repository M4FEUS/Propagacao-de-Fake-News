# Trabalho Prático — Propagação de Fake News em Sistemas Paralelos e Distribuídos

Simulação de propagação de informação em uma grade 2D, onde cada célula representa uma pessoa em um de vários estados possíveis. O projeto inclui inovações de modelagem (agências de checagem, modo competitivo), implementações Sequencial, Paralela e Distribuída, e um pipeline completo de benchmark e análise de desempenho.

## Estados da simulação

| Constante      | Valor | Significado                                                   |
|----------------|-------|-----------------------------------------------------------------|
| `IGNORANTE`    | 0     | Ainda não recebeu ou não acredita na informação                |
| `ESPALHADOR_A` | 1     | Acredita e compartilha a fake news tipo A                      |
| `INATIVO`      | 2     | Já recebeu a informação, mas não espalha mais                  |
| `ESPALHADOR_B` | 3     | Acredita e compartilha a fake news tipo B (modo competitivo)   |
| `AGENCIA`      | 4     | Agência de checagem (aumenta a resistência local)               |

## Arquivos do projeto

| Arquivo                   | Descrição                                                                                   |
|-----------------------------|--------------------------------------------------------------------------------------------|
| `fakenews_original.py`      | Versão original do professor (usa `deepcopy`)                                              |
| `fakenews_sequencial.py`    | Versão sequencial otimizada — **código base para M2/M3**                                   |
| `FakeNews.py`                | Código fonte inicial fornecido pelo professor                                              |
| `fakenews_paralelo.py`      | Versão paralela (M2) — distribui o processamento entre múltiplos processos                 |
| `servidor.py`               | Versão distribuída (M3) — orquestra o processamento via Sockets entre clientes e servidor   |
| `cliente.py`                | Cliente da versão distribuída (M3) — conecta ao `servidor.py` via Sockets para processar parte da grade |
| `visualizacao.py`           | Gera a animação gráfica (Matplotlib) da propagação                                          |
| `benchmark.py`               | Pipeline completo de testes (Sequencial, Paralelo e Distribuído) e extração de métricas (CSV) |
| `analise_graficos.py`       | Script de análise de dados (Pandas) que gera os 4 gráficos comparativos de desempenho        |
| `grafico_1_tempo_vs_tamanho.png` | Gráfico gerado automaticamente: tempo de execução vs. tamanho da matriz (Sequencial, Paralela e Distribuída) |
| `grafico_2_speedup.png`     | Gráfico gerado automaticamente: curvas de Speedup da versão Paralela e Distribuída vs. linha ideal (linear) |
| `grafico_3_eficiencia.png`  | Gráfico gerado automaticamente: curvas de Eficiência da versão Paralela e Distribuída conforme o escalamento |
| `grafico_4_gargalo_rede.png` | Gráfico gerado automaticamente: tempo distribuído (M3) vs. número de clientes, evidenciando o gargalo de rede |
| `LICENSE`                    | Licença do projeto                                                                          |

## Requisitos

- Python 3.8 ou superior
- O núcleo da simulação (`fakenews_sequencial.py`, `fakenews_original.py`, `fakenews_paralelo.py`) não possui dependências externas.
- Para visualização, gráficos de benchmark e análise de dados, é necessário instalar:

```bash
pip install matplotlib pandas
```

## Execução

### Versão sequencial (código base)

```bash
python fakenews_sequencial.py --linhas 100 --colunas 100 --geracoes 50
```

### Todos os parâmetros disponíveis

```bash
python fakenews_sequencial.py \
    --linhas 100 \
    --colunas 100 \
    --geracoes 50 \
    --espalhadores 0.05 \
    --semente 42 \
    --limiar 3 \
    --multiplas-noticias \
    --probabilidade-variavel \
    --mostrar-grade
```

| Argumento                   | Tipo  | Padrão | Descrição                                                          |
|-------------------------------|-------|--------|------------------------------------------------------------------------|
| `--linhas`                   | int   | 100    | Número de linhas da grade                                              |
| `--colunas`                  | int   | 100    | Número de colunas da grade                                             |
| `--geracoes`                 | int   | 50     | Número máximo de gerações                                              |
| `--espalhadores`             | float | 0.02   | Fração inicial de espalhadores (ex.: 0.05 = 5%)                        |
| `--semente`                  | int   | 42     | Semente aleatória para reprodutibilidade                               |
| `--limiar`                   | int   | 2      | Vizinhos espalhadores necessários para converter um ignorante          |
| `--multiplas-noticias`       | flag  | —      | Ativa o modo competitivo, com duas fake news (A vs. B)                 |
| `--probabilidade-variavel`   | flag  | —      | Ativa credulidade individual por célula (ignora o limiar fixo)         |
| `--mostrar-grade`            | flag  | —      | Imprime a grade a cada geração (recomendado só para grades pequenas)   |

### Versão original (baseline)

```bash
python fakenews_original.py
```

> Mantida para fins de comparação de desempenho com a versão otimizada (M2/M3); usa `deepcopy` a cada geração.

### Versão paralela (M2)

```bash
python fakenews_paralelo.py --processos 4
```

> O `benchmark.py` automatiza a execução dessa versão variando de 1 a 8 processos. Parâmetros adicionais de CLI não foram detalhados nas informações repassadas — confirmar no código-fonte.

### Versão distribuída (M3)

```bash
python servidor.py --auto
```

> A flag `--auto` abre e gerencia os Sockets dos clientes (`cliente.py`) automaticamente, sendo usada pelo `benchmark.py` para os testes distribuídos. Demais parâmetros não foram detalhados — confirmar no código-fonte.

## Regras da simulação e inovações

1. **Agências de checagem**: 1% da grade inicial é composta por Agências (`AGENCIA`), definidas na inicialização. Elas nunca mudam de estado. Se um `IGNORANTE` tiver uma Agência em sua vizinhança, seu limiar de convencimento aumenta em 3 (ganha resistência).
2. **Ignorante → Espalhador**: a célula muda de estado se atingir o limiar exigido de vizinhos espalhadores (vizinhança de Moore, até 8 vizinhos). No modo competitivo (`--multiplas-noticias`), a célula assume a fake news (A ou B) predominante entre seus vizinhos.
3. **Espalhador → Inativo**: na geração seguinte, o espalhador obrigatoriamente para de compartilhar.
4. **Inativo → Inativo**: estado permanente.

A simulação encerra antecipadamente quando não restam espalhadores ativos (tipo A ou B) na grade.

## Ferramentas de análise (M4)

### Visualização animada

Para assistir à propagação da fake news interagindo com as Agências de Checagem:

```bash
python visualizacao.py
```

### Pipeline de benchmark (Sequencial + Paralelo + Distribuído)

O `benchmark.py` executa um loop triplo, testando todas as combinações de tamanho de matriz, número de gerações e percentual de espalhadores, e integra as três versões do projeto:

- **Sequencial**: roda `fakenews_sequencial.py` como linha de base de comparação.
- **Paralelo (M2)**: executa `fakenews_paralelo.py` variando de 1 a 8 processos.
- **Distribuído (M3)**: executa `servidor.py --auto`, que abre e gerencia os Sockets dos clientes (`cliente.py`) automaticamente durante o teste.

```bash
python benchmark.py
```

O resultado é salvo em `resultados_benchmark.csv`, usado no cálculo de Speedup e Eficiência.

### Análise de gráficos (Tempo, Speedup, Eficiência e Gargalo de Rede)

O `analise_graficos.py` lê o `resultados_benchmark.csv` com Pandas e gera 4 gráficos comparativos:

1. **Gráfico 1 — Tempo vs. Tamanho da Matriz**: plota o tempo de execução (eixo Y) pelo tamanho da matriz (eixo X), com as três versões (Sequencial, Paralela e Distribuída) na mesma imagem, evidenciando como a versão sequencial "explode" em tempo enquanto as otimizadas se mantêm estáveis.
2. **Gráfico 2 — Speedup** ($S = T_{seq} / T_{par}$): calcula e plota as curvas da versão Paralela e da Distribuída juntas no mesmo gráfico, permitindo comparar diretamente o desempenho de cada uma frente à Lei de Amdahl.
3. **Gráfico 3 — Eficiência** ($E = S / N$): mesma lógica do Speedup, com as curvas da Paralela e da Distribuída sobrepostas no mesmo gráfico.
4. **Gráfico 4 — Gargalo de Rede (M3)**: gráfico exclusivo que isola os testes da versão Distribuída, plotando tempo distribuído × número de clientes, evidenciando como o aumento de clientes (e do tráfego de Sockets) afeta o tempo total.

```bash
python analise_graficos.py
```

O script também conta com automação e tratamento de erros:

- Filtra automaticamente o cenário ideal para o cálculo de Speedup (usa a matriz mais pesada, 1000×1000).
- Não quebra mais se faltarem dados de alguma versão no `resultados_benchmark.csv`.

Esse script gera automaticamente:

- `grafico_1_tempo_vs_tamanho.png` — tempo de execução vs. tamanho da matriz (Sequencial, Paralela e Distribuída).
- `grafico_2_speedup.png` — curvas de Speedup da versão Paralela e Distribuída.
- `grafico_3_eficiencia.png` — curvas de Eficiência da versão Paralela e Distribuída.
- `grafico_4_gargalo_rede.png` — tempo distribuído × número de clientes (M3).

## Resultados e conclusões técnicas

Com o pipeline completo rodando, os gráficos comprovaram na prática os seguintes conceitos teóricos:

1. **Lei de Amdahl**: o ganho de tempo tem um limite. Conforme mais processos são adicionados, a fração de código que não pode ser paralelizada (ex.: sincronização e troca de mensagens) achata a curva de aceleração.
2. **Gargalo de rede vs. gargalo de CPU**: a versão distribuída (M3) sofre severamente com o tempo de envio de dados via Sockets pela rede. Ao usar 4 clientes em matrizes grandes, o tempo gasto trafegando dados supera o tempo de cálculo da CPU, derrubando a eficiência do sistema para a casa dos 68%.

## Uso programático (para M2 e M3)

As funções principais podem ser importadas diretamente. O `fakenews_sequencial.py` aplica a técnica de *double buffering* (duas matrizes alternadas) para evitar os custos de memória do `deepcopy`.

```python
from fakenews_sequencial import (
    IGNORANTE, ESPALHADOR_A, ESPALHADOR_B, INATIVO, AGENCIA,
    criar_grade, criar_grade_vazia,
    proxima_geracao, contar_estados,
    simular_sem_imprimir,
)

grade_final = simular_sem_imprimir(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.05,
    limiar_convencimento=3,
    semente=42,
    multiplas_noticias=True,
)
```

A função `proxima_geracao(grade_atual, grade_destino, limiar_convencimento, multiplas_noticias, matriz_credulidade)` lê da matriz atual e escreve diretamente na matriz de destino, sem utilizar `deepcopy`. Essa técnica de *double buffering* é o que garante a eficiência de memória para a paralelização.
