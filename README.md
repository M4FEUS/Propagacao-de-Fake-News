# Trabalho Prático — Propagação de Fake News em Sistemas Paralelos e Distribuídos

Simulação de propagação de informação em uma grade 2D, onde cada célula representa uma pessoa em um de três estados:

| Constante   | Valor | Significado                                      |
|-------------|-------|--------------------------------------------------|
| `IGNORANTE` | 0     | Ainda não recebeu ou não acredita na informação  |
| `ESPALHADOR`| 1     | Acredita e compartilha a fake news                |
| `INATIVO`   | 2     | Já recebeu a informação, mas não espalha mais    |

## Arquivos do projeto

| Arquivo                  | Descrição                                              |
|--------------------------|--------------------------------------------------------|
| `fakenews_original.py`   | Versão original do professor (usa `deepcopy`)          |
| `fakenews_sequencial.py` | Versão sequencial otimizada — **código base para M2/M3** |
| `FakeNews.py`            | Código fonte inicial fornecido pelo professor          |

## Requisitos

- Python 3.8 ou superior
- Nenhuma dependência externa (apenas biblioteca padrão)

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
    --mostrar-grade
```

| Argumento          | Tipo  | Padrão | Descrição                                              |
|--------------------|-------|--------|--------------------------------------------------------|
| `--linhas`         | int   | 100    | Número de linhas da grade                              |
| `--colunas`        | int   | 100    | Número de colunas da grade                             |
| `--geracoes`       | int   | 50     | Número máximo de gerações                              |
| `--espalhadores`   | float | 0.02   | Fração inicial de espalhadores (ex.: 0.05 = 5%)      |
| `--semente`        | int   | 42     | Semente aleatória para reprodutibilidade               |
| `--limiar`         | int   | 2      | Vizinhos espalhadores para converter um ignorante      |
| `--mostrar-grade`  | flag  | —      | Imprime a grade a cada geração (grades pequenas)       |

### Versão original (baseline)

```bash
python fakenews_original.py
```

## Regras da simulação

1. **Ignorante → Espalhador**: se a célula tiver pelo menos `--limiar` vizinhos espalhadores (vizinhança de Moore, até 8 vizinhos).
2. **Espalhador → Inativo**: na geração seguinte, o espalhador para de compartilhar.
3. **Inativo → Inativo**: estado permanente.

A simulação encerra antecipadamente quando não restam espalhadores.

## Uso programático (para M2 e M3)

As funções principais podem ser importadas diretamente:

```python
from fakenews_sequencial import (
    IGNORANTE, ESPALHADOR, INATIVO,
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
)
```

`proxima_geracao(grade_atual, grade_destino, limiar_convencimento)` lê da matriz atual e escreve na outra, sem `deepcopy`.
