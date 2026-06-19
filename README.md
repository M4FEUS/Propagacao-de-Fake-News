# Trabalho Prático — Propagação de Fake News em Sistemas Paralelos e Distribuídos

Simulação de propagação de informação em uma grade 2D, onde cada célula representa uma pessoa em um de vários estados possíveis. O projeto inclui inovações de modelagem (agências de checagem, modo competitivo) e ferramentas de visualização e benchmark para análise de desempenho.

## Estados da simulação

| Constante      | Valor | Significado                                                   |
|----------------|-------|-----------------------------------------------------------------|
| `IGNORANTE`    | 0     | Ainda não recebeu ou não acredita na informação                |
| `ESPALHADOR_A` | 1     | Acredita e compartilha a fake news tipo A                      |
| `INATIVO`      | 2     | Já recebeu a informação, mas não espalha mais                  |
| `ESPALHADOR_B` | 3     | Acredita e compartilha a fake news tipo B (modo competitivo)   |
| `AGENCIA`      | 4     | Agência de checagem (aumenta a resistência local)               |

## Arquivos do projeto

| Arquivo                   | Descrição                                                     |
|-----------------------------|------------------------------------------------------------------|
| `fakenews_original.py`      | Versão original do professor (usa `deepcopy`)                  |
| `fakenews_sequencial.py`    | Versão sequencial otimizada — **código base para M2/M3**       |
| `FakeNews.py`                | Código fonte inicial fornecido pelo professor                  |
| `visualizacao.py`           | Gera a animação gráfica (Matplotlib) da propagação              |
| `benchmark.py`               | Pipeline automatizado de testes e extração de métricas (CSV)    |

## Requisitos

- Python 3.8 ou superior
- O núcleo da simulação (`fakenews_sequencial.py`, `fakenews_original.py`) não possui dependências externas.
- Para executar `visualizacao.py` ou gerar gráficos a partir do `benchmark.py`, é necessário instalar o Matplotlib:

```bash
pip install matplotlib
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

### Pipeline de benchmark

Para rodar a bateria de testes automatizados, variando o tamanho das matrizes, e gerar o `resultados_benchmark.csv` (usado no cálculo de Speedup e Eficiência):

```bash
python benchmark.py
```

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

`proxima_geracao(grade_atual, grade_destino, limiar_convencimento, ...)` lê da matriz atual e escreve na outra, sem `deepcopy`.

> ⚠️ A assinatura exata da função pode ter ganhado parâmetros adicionais para suportar o modo competitivo (`ESPALHADOR_B`) e as Agências (`AGENCIA`). Vale conferir o código-fonte atual antes de considerar este trecho definitivo.
