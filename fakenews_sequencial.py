"""
Simulação sequencial de Propagação de Fake News (sem deepcopy).

Usa duas matrizes (grade_a, grade_b) que se alternam a cada geração:
leitura sempre na matriz atual, escrita na outra.

Este módulo serve como código base para as versões paralela (M2) e distribuída (M3).
"""

import argparse
import random
import time

# ---------------------------------------------------------------------------
# Constantes de estado da simulação
# ---------------------------------------------------------------------------
# Cada célula da grade representa uma pessoa em exatamente um destes estados.
# Os valores inteiros são usados internamente e como chaves em contagem de estados.

IGNORANTE = 0     # Ainda não recebeu ou não acredita na informação.
ESPALHADOR_A = 1  # Espalha a fake news tipo A (modo competitivo).
ESPALHADOR = 1    # Alias de ESPALHADOR_A para compatibilidade com modo simples.
INATIVO = 2       # Já recebeu a informação, mas não a espalha mais.
ESPALHADOR_B = 3  # Espalha a fake news tipo B (modo competitivo).

ESTADOS_ESPALHADORES = (ESPALHADOR_A, ESPALHADOR_B)


def criar_grade(
    linhas,
    colunas,
    percentual_espalhadores=0.02,
    semente=42,
    multiplas_noticias=False,
):
    """
    Cria a grade inicial da simulação.

    A maior parte da população começa como IGNORANTE. Uma fração definida por
    `percentual_espalhadores` é sorteada aleatoriamente como espalhadora.

    No modo simples, cada espalhador inicial usa ESPALHADOR (= ESPALHADOR_A).
    No modo competitivo (`multiplas_noticias=True`), os espalhadores iniciais
    são divididos aleatoriamente entre ESPALHADOR_A e ESPALHADOR_B.

    Parâmetros
    ----------
    linhas : int
        Número de linhas da grade.
    colunas : int
        Número de colunas da grade.
    percentual_espalhadores : float, opcional
        Fração da população que inicia como espalhadora (padrão: 0.02 = 2%).
    semente : int, opcional
        Semente do gerador pseudoaleatório para reprodutibilidade (padrão: 42).
    multiplas_noticias : bool, opcional
        Se True, inicializa espalhadores tipo A e B competindo (padrão: False).

    Retorno
    -------
    list[list[int]]
        Matriz bidimensional com os estados iniciais da simulação.
    """
    if semente is not None:
        random.seed(semente)

    grade = [[IGNORANTE for _ in range(colunas)] for _ in range(linhas)]

    total_celulas = linhas * colunas
    total_espalhadores = int(total_celulas * percentual_espalhadores)

    for _ in range(total_espalhadores):
        i = random.randint(0, linhas - 1)
        j = random.randint(0, colunas - 1)
        if multiplas_noticias:
            grade[i][j] = ESPALHADOR_A if random.random() < 0.5 else ESPALHADOR_B
        else:
            grade[i][j] = ESPALHADOR

    return grade


def criar_grade_vazia(linhas, colunas):
    """
    Cria uma matriz pré-alocada para receber a próxima geração.

    Todas as células são inicializadas como IGNORANTE; `proxima_geracao`
    sobrescreve cada posição com o estado calculado.

    Parâmetros
    ----------
    linhas : int
        Número de linhas da grade.
    colunas : int
        Número de colunas da grade.

    Retorno
    -------
    list[list[int]]
        Matriz bidimensional vazia (preenchida com IGNORANTE).
    """
    return [[IGNORANTE for _ in range(colunas)] for _ in range(linhas)]


def contar_vizinhos_espalhadores(grade, i, j):
    """
    Conta quantos vizinhos de Moore estão espalhando (modo simples).

    Vizinhança de Moore: as 8 células adjacentes à posição (i, j), incluindo
    diagonais. A própria célula central é ignorada.

    Exemplo — vizinhos considerados para a célula marcada com X:

        A B C
        D X E
        F G H

    Apenas A, B, C, D, E, F, G e H entram na contagem. Células fora dos
    limites da grade são descartadas (bordas têm menos de 8 vizinhos).

    Parâmetros
    ----------
    grade : list[list[int]]
        Grade da geração atual (somente leitura).
    i : int
        Índice da linha da célula central.
    j : int
        Índice da coluna da célula central.

    Retorno
    -------
    int
        Quantidade de vizinhos no estado ESPALHADOR (0 a 8).
    """
    viz_a, viz_b = contar_vizinhos_por_tipo(grade, i, j)
    return viz_a + viz_b


def contar_vizinhos_por_tipo(grade, i, j):
    """
    Conta vizinhos de Moore separados por tipo de fake news.

    Usado no modo competitivo (Daley-Kendall estendido): cada ignorante
    compara a pressão de vizinhos ESPALHADOR_A e ESPALHADOR_B.

    Parâmetros
    ----------
    grade : list[list[int]]
        Grade da geração atual (somente leitura).
    i : int
        Índice da linha da célula central.
    j : int
        Índice da coluna da célula central.

    Retorno
    -------
    tuple[int, int]
        Tupla (vizinhos_tipo_a, vizinhos_tipo_b), cada valor entre 0 e 8.
    """
    linhas = len(grade)
    colunas = len(grade[0])

    viz_a = 0
    viz_b = 0

    # Percorre os deslocamentos (di, dj) em {-1, 0, 1} — vizinhança de Moore.
    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            if di == 0 and dj == 0:
                continue

            ni = i + di
            nj = j + dj

            if 0 <= ni < linhas and 0 <= nj < colunas:
                if grade[ni][nj] == ESPALHADOR_A:
                    viz_a += 1
                elif grade[ni][nj] == ESPALHADOR_B:
                    viz_b += 1

    return viz_a, viz_b


def proxima_geracao(
    grade_atual,
    grade_destino,
    limiar_convencimento=2,
    multiplas_noticias=False,
    matriz_credulidade=None,
):
    """
    Calcula a próxima geração lendo de `grade_atual` e escrevendo em `grade_destino`.

    Modo simples (`multiplas_noticias=False`):
    - IGNORANTE → ESPALHADOR se houver >= `limiar_convencimento` vizinhos
      espalhadores; caso contrário permanece IGNORANTE.
    - ESPALHADOR → INATIVO na geração seguinte.
    - INATIVO → INATIVO (estado absorvente).

    Modo probabilístico (quando `matriz_credulidade` é informada):
    - Substitui a verificação por limiar fixo. O ignorante é convertido se
      (total_vizinhos / 8.0) >= credulidade[i][j].

    Modo competitivo (`multiplas_noticias=True`, Daley-Kendall estendido):
    - IGNORANTE compara vizinhos ESPALHADOR_A e ESPALHADOR_B separadamente.
    - Se a soma de vizinhos espalhadores >= `limiar_convencimento`:
        - mais vizinhos tipo A → ESPALHADOR_A;
        - mais vizinhos tipo B → ESPALHADOR_B;
        - empate → permanece IGNORANTE.
    - ESPALHADOR_A ou ESPALHADOR_B → INATIVO na geração seguinte.
    - INATIVO → INATIVO (estado absorvente).

    Parâmetros
    ----------
    grade_atual : list[list[int]]
        Grade da geração corrente (somente leitura).
    grade_destino : list[list[int]]
        Grade onde o resultado da próxima geração será escrito.
    limiar_convencimento : int, opcional
        Número mínimo de vizinhos espalhadores para converter um ignorante
        (padrão: 2).
    multiplas_noticias : bool, opcional
        Ativa a competição entre fake news A e B (padrão: False).

    Retorno
    -------
    None
        O resultado é escrito diretamente em `grade_destino`.
    """
    linhas = len(grade_atual)
    colunas = len(grade_atual[0])

    for i in range(linhas):
        for j in range(colunas):
            estado = grade_atual[i][j]

            if estado == IGNORANTE:
                if multiplas_noticias:
                    viz_a, viz_b = contar_vizinhos_por_tipo(grade_atual, i, j)
                    total_vizinhos = viz_a + viz_b

                    converte = False
                    if matriz_credulidade is not None:
                        converte = (total_vizinhos / 8.0) >= matriz_credulidade[i][j]
                    else:
                        converte = total_vizinhos >= limiar_convencimento

                    if converte:
                        if viz_a > viz_b:
                            grade_destino[i][j] = ESPALHADOR_A
                        elif viz_b > viz_a:
                            grade_destino[i][j] = ESPALHADOR_B
                        else:
                            grade_destino[i][j] = IGNORANTE
                    else:
                        grade_destino[i][j] = IGNORANTE
                else:
                    vizinhos = contar_vizinhos_espalhadores(grade_atual, i, j)

                    converte = False
                    if matriz_credulidade is not None:
                        converte = (vizinhos / 8.0) >= matriz_credulidade[i][j]
                    else:
                        converte = vizinhos >= limiar_convencimento

                    if converte:
                        grade_destino[i][j] = ESPALHADOR
                    else:
                        grade_destino[i][j] = IGNORANTE

            elif estado in ESTADOS_ESPALHADORES or estado == ESPALHADOR:
                grade_destino[i][j] = INATIVO

            else:
                grade_destino[i][j] = INATIVO


def contar_estados(grade):
    """
    Conta quantas células existem em cada estado.

    Parâmetros
    ----------
    grade : list[list[int]]
        Grade a ser analisada.

    Retorno
    -------
    dict[int, int]
        Dicionário com totais por estado. Inclui IGNORANTE, ESPALHADOR
        (modo simples), ESPALHADOR_A, ESPALHADOR_B e INATIVO.
    """
    contagem = {
        IGNORANTE: 0,
        ESPALHADOR: 0,
        ESPALHADOR_A: 0,
        ESPALHADOR_B: 0,
        INATIVO: 0,
    }

    for linha in grade:
        for celula in linha:
            contagem[celula] = contagem.get(celula, 0) + 1

    return contagem


def total_espalhadores_ativos(contagem):
    """
    Retorna o total de células espalhando em qualquer modo de simulação.

    Parâmetros
    ----------
    contagem : dict[int, int]
        Resultado de `contar_estados`.

    Retorno
    -------
    int
        Soma de ESPALHADOR, ESPALHADOR_A e ESPALHADOR_B.
    """
    return (
        contagem.get(ESPALHADOR, 0)
        + contagem.get(ESPALHADOR_A, 0)
        + contagem.get(ESPALHADOR_B, 0)
    )


def imprimir_grade(grade, limite=30, multiplas_noticias=False):
    """
    Exibe uma parte da grade no terminal para depuração ou demonstração.

    Símbolos (modo simples): '.' = IGNORANTE, 'E' = ESPALHADOR, 'N' = INATIVO.
    Símbolos (modo competitivo): '.' = IGNORANTE, 'A' = ESPALHADOR_A,
    'B' = ESPALHADOR_B, 'N' = INATIVO.

    Parâmetros
    ----------
    grade : list[list[int]]
        Grade a ser exibida.
    limite : int, opcional
        Número máximo de linhas e colunas a imprimir (padrão: 30).
    multiplas_noticias : bool, opcional
        Se True, usa símbolos A/B para os dois tipos de espalhador (padrão: False).

    Retorno
    -------
    None
    """
    simbolos = {
        IGNORANTE: ".",
        ESPALHADOR: "E",
        ESPALHADOR_A: "A",
        ESPALHADOR_B: "B",
        INATIVO: "N",
    }

    linhas = min(len(grade), limite)
    colunas = min(len(grade[0]), limite)

    for i in range(linhas):
        linha = ""
        for j in range(colunas):
            linha += simbolos[grade[i][j]] + " "
        print(linha)
    print()


def executar_simulacao(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    limiar_convencimento=2,
    mostrar_grade=False,
    semente=42,
    multiplas_noticias=False,
    probabilidade_variavel=False,
):
    """
    Executa a simulação sequencial completa com double buffering.

    A cada geração, `proxima_geracao` lê de `grade_a` e escreve em `grade_b`;
    em seguida as referências são trocadas. A simulação pode encerrar antes de
    `geracoes` se não restarem espalhadores.

    Parâmetros
    ----------
    linhas : int, opcional
        Número de linhas da grade (padrão: 100).
    colunas : int, opcional
        Número de colunas da grade (padrão: 100).
    geracoes : int, opcional
        Número máximo de gerações a simular (padrão: 50).
    percentual_espalhadores : float, opcional
        Fração inicial de espalhadores (padrão: 0.02).
    limiar_convencimento : int, opcional
        Vizinhos espalhadores necessários para converter um ignorante (padrão: 2).
    mostrar_grade : bool, opcional
        Se True, imprime a grade a cada geração (padrão: False).
    semente : int, opcional
        Semente aleatória para a grade inicial (padrão: 42).
    multiplas_noticias : bool, opcional
        Ativa competição entre fake news A e B (padrão: False).
    probabilidade_variavel : bool, opcional
        Substitui o limiar fixo por coeficiente de credulidade individual (padrão: False).

    Retorno
    -------
    list[list[int]]
        Grade final após a última geração simulada.
    """
    grade_a = criar_grade(
        linhas,
        colunas,
        percentual_espalhadores,
        semente,
        multiplas_noticias,
    )
    grade_b = criar_grade_vazia(linhas, colunas)

    matriz_credulidade = None
    if probabilidade_variavel:
        matriz_credulidade = [[random.random() for _ in range(colunas)] for _ in range(linhas)]

    titulo = (
        "=== SIMULAÇÃO COMPETITIVA DE FAKE NEWS (A vs B) ==="
        if multiplas_noticias
        else "=== SIMULAÇÃO SEQUENCIAL DE PROPAGAÇÃO DE FAKE NEWS ==="
    )
    print(titulo)
    print(f"Tamanho da grade: {linhas} x {colunas} ({linhas*colunas:,} pessoas)")
    print(f"Gerações: {geracoes}")
    contagem_inicial = contar_estados(grade_a)

    if multiplas_noticias:
        total_inicial = (
            contagem_inicial[ESPALHADOR_A] + contagem_inicial[ESPALHADOR_B]
        )
        print(
            f"Percentual inicial de espalhadores: "
            f"{percentual_espalhadores * 100:.2f}% "
            f"({total_inicial:,} espalhadores: "
            f"A={contagem_inicial[ESPALHADOR_A]:,}, "
            f"B={contagem_inicial[ESPALHADOR_B]:,})"
        )
    else:
        print(
            f"Percentual inicial de espalhadores: "
            f"{percentual_espalhadores * 100:.2f}% "
            f"({contagem_inicial[ESPALHADOR]:,} espalhadores reais)"
        )

    if probabilidade_variavel:
        print("Limiar de convencimento: Individual (credulidade variável)")
    else:
        print(f"Limiar de convencimento: {limiar_convencimento} vizinhos")

    print(f"Semente: {semente}")
    if multiplas_noticias:
        print("Modo: múltiplas notícias (competição Daley-Kendall estendida)")
    print()

    inicio = time.time()

    for geracao in range(geracoes):
        proxima_geracao(
            grade_a,
            grade_b,
            limiar_convencimento,
            multiplas_noticias,
            matriz_credulidade,
        )
        grade_a, grade_b = grade_b, grade_a

        contagem = contar_estados(grade_a)

        if multiplas_noticias:
            print(
                f"Geração {geracao + 1:03d} | "
                f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
                f"Esp. A: {contagem[ESPALHADOR_A]:>8,} | "
                f"Esp. B: {contagem[ESPALHADOR_B]:>8,} | "
                f"Inativos: {contagem[INATIVO]:>10,}"
            )
        else:
            print(
                f"Geração {geracao + 1:03d} | "
                f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
                f"Espalhadores: {contagem[ESPALHADOR]:>10,} | "
                f"Inativos: {contagem[INATIVO]:>10,}"
            )

        if mostrar_grade:
            imprimir_grade(grade_a, multiplas_noticias=multiplas_noticias)

        if total_espalhadores_ativos(contagem) == 0:
            print("\nA propagação terminou: não há mais espalhadores.")
            break

    fim = time.time()

    tempo_total = fim - inicio

    print()
    print("=== RESULTADO FINAL ===")
    print(f"Tempo total de execução: {tempo_total:.4f} segundos")

    contagem_final = contar_estados(grade_a)
    total = linhas * colunas

    print(f"Ignorantes finais: {contagem_final[IGNORANTE]:,} ({contagem_final[IGNORANTE] / total * 100:,.2f}%)")

    if multiplas_noticias:
        print(
            f"Espalhadores A finais: {contagem_final[ESPALHADOR_A]:,} "
            f"({contagem_final[ESPALHADOR_A] / total * 100:,.2f}%)"
        )
        print(
            f"Espalhadores B finais: {contagem_final[ESPALHADOR_B]:,} "
            f"({contagem_final[ESPALHADOR_B] / total * 100:,.2f}%)"
        )
    else:
        print(
            f"Espalhadores finais: {contagem_final[ESPALHADOR]:,} "
            f"({contagem_final[ESPALHADOR] / total * 100:,.2f}%)"
        )

    print(f"Inativos finais: {contagem_final[INATIVO]:,} ({contagem_final[INATIVO] / total * 100:,.2f}%)")

    return grade_a


def simular_sem_imprimir(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    limiar_convencimento=2,
    semente=42,
    multiplas_noticias=False,
    probabilidade_variavel=False,
):
    """
    Executa a simulação e retorna a grade final, sem imprimir no terminal.

    Útil para testes automatizados e comparação com outras versões (original,
    paralela, distribuída).

    Parâmetros
    ----------
    linhas : int, opcional
        Número de linhas da grade (padrão: 100).
    colunas : int, opcional
        Número de colunas da grade (padrão: 100).
    geracoes : int, opcional
        Número máximo de gerações (padrão: 50).
    percentual_espalhadores : float, opcional
        Fração inicial de espalhadores (padrão: 0.02).
    limiar_convencimento : int, opcional
        Vizinhos espalhadores necessários para converter um ignorante (padrão: 2).
    semente : int, opcional
        Semente aleatória (padrão: 42).
    multiplas_noticias : bool, opcional
        Ativa competição entre fake news A e B (padrão: False).
    probabilidade_variavel : bool, opcional
        Substitui limiar fixo por credulidade individual (padrão: False).

    Retorno
    -------
    list[list[int]]
        Grade final após a simulação.
    """
    grade_a = criar_grade(
        linhas,
        colunas,
        percentual_espalhadores,
        semente,
        multiplas_noticias,
    )
    grade_b = criar_grade_vazia(linhas, colunas)

    matriz_credulidade = None
    if probabilidade_variavel:
        matriz_credulidade = [[random.random() for _ in range(colunas)] for _ in range(linhas)]

    for _ in range(geracoes):
        proxima_geracao(
            grade_a,
            grade_b,
            limiar_convencimento,
            multiplas_noticias,
            matriz_credulidade,
        )
        grade_a, grade_b = grade_b, grade_a
        if total_espalhadores_ativos(contar_estados(grade_a)) == 0:
            break

    return grade_a


def parse_argumentos():
    """
    Define e interpreta os argumentos de linha de comando.

    Retorno
    -------
    argparse.Namespace
        Objeto com os parâmetros da simulação.
    """
    parser = argparse.ArgumentParser(
        description="Simulação sequencial de propagação de fake news em uma grade 2D."
    )
    parser.add_argument(
        "--linhas", type=int, default=100,
        help="Número de linhas da grade (padrão: 100)"
    )
    parser.add_argument(
        "--colunas", type=int, default=100,
        help="Número de colunas da grade (padrão: 100)"
    )
    parser.add_argument(
        "--geracoes", type=int, default=50,
        help="Número máximo de gerações (padrão: 50)"
    )
    parser.add_argument(
        "--espalhadores", type=float, default=0.02,
        help="Percentual inicial de espalhadores, entre 0 e 1 (padrão: 0.02)"
    )
    parser.add_argument(
        "--semente", type=int, default=42,
        help="Semente do gerador aleatório (padrão: 42). Use -1 para não fixar a semente."
    )
    parser.add_argument(
        "--limiar", type=int, default=2,
        help="Vizinhos espalhadores necessários para converter um ignorante (padrão: 2)"
    )
    parser.add_argument(
        "--mostrar-grade", action="store_true",
        help="Imprime a grade a cada geração (útil para grades pequenas)"
    )
    parser.add_argument(
        "--multiplas-noticias", action="store_true",
        help="Ativa modo competitivo com duas fake news (A vs B, Daley-Kendall estendido)"
    )
    parser.add_argument(
        "--probabilidade-variavel", action="store_true",
        help="Ativa o modo com credulidade individual variável (ignora limiar fixo)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_argumentos()

    semente_valida = args.semente if args.semente >= 0 else None

    executar_simulacao(
        linhas=args.linhas,
        colunas=args.colunas,
        geracoes=args.geracoes,
        percentual_espalhadores=args.espalhadores,
        limiar_convencimento=args.limiar,
        mostrar_grade=args.mostrar_grade,
        semente=semente_valida,
        multiplas_noticias=args.multiplas_noticias,
        probabilidade_variavel=args.probabilidade_variavel,
    )
