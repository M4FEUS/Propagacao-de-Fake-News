"""
Simulação sequencial de Propagação de Fake News

Estados:
0 = Ignorante: ainda não recebeu/acredita na informação
1 = Espalhador: acredita e compartilha a informação
2 = Inativo: recebeu a informação, mas não compartilha mais

Fluxograma básico:
Início
  ↓
Criar grade inicial
  ↓
Para cada geração
  ↓
Calcular próxima geração usando a grade atual
  ↓
Contar estados
  ↓
Imprimir estatísticas
  ↓
Ainda existem espalhadores e ainda há gerações?
  ↓ sim
Próxima geração
  ↓
Calcular próxima geração usando a grade atual
  ↓ não
Resultado final

"""

import random
import time
from copy import deepcopy
# o deepcopy garante independência, as alterações em objetos 
# aninhados não afetam o original

IGNORANTE = 0
ESPALHADOR = 1
INATIVO = 2


def criar_grade(linhas, colunas, percentual_espalhadores=0.02, semente=42):
    """
    Cria uma matriz inicial.
    A maior parte da população começa ignorante.
    Uma pequena parte começa como espalhadora da fake news.
    """
    random.seed(semente)

    grade = [[IGNORANTE for _ in range(colunas)] for _ in range(linhas)]

    total_celulas = linhas * colunas
    total_espalhadores = int(total_celulas * percentual_espalhadores)

    for _ in range(total_espalhadores):
        i = random.randint(0, linhas - 1)
        j = random.randint(0, colunas - 1)
        grade[i][j] = ESPALHADOR

    return grade


def contar_vizinhos_espalhadores(grade, i, j):
    """
    Conta quantos vizinhos ao redor da célula estão espalhando a fake news.
    Usa vizinhança de Moore: até 8 vizinhos.
    A vizinhança de Moore é o conjunto das 8 células ao redor de uma célula 
    central em uma matriz 2D.
    Por exemplo considere X em:
    A B C
    D X E
    F G H
    a vizinhança de Moore seria:
    A B C
    D   E
    F G H    
    """
    linhas = len(grade)
    colunas = len(grade[0])

    total = 0

    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            # Quando di == 0 e dj == 0, temos a própria célula central, que deve ser ignorada.
            if di == 0 and dj == 0:
                continue

            ni = i + di
            nj = j + dj

            if 0 <= ni < linhas and 0 <= nj < colunas:
                if grade[ni][nj] == ESPALHADOR:
                    total += 1

    return total


def proxima_geracao(grade, limiar_convencimento=2):
    """
    Calcula a próxima geração da simulação.

    Regra simplificada:
    - Ignorante vira espalhador se tiver pelo menos 'limiar_convencimento'
      vizinhos espalhadores.
    - Espalhador vira inativo na próxima geração.
    - Inativo permanece inativo.

    Importante:
    Usa uma nova matriz para evitar atualização "ao vivo".
    """
    linhas = len(grade)
    colunas = len(grade[0])

    nova_grade = deepcopy(grade)

    for i in range(linhas):
        for j in range(colunas):

            if grade[i][j] == IGNORANTE:
                vizinhos = contar_vizinhos_espalhadores(grade, i, j)

                if vizinhos >= limiar_convencimento:
                    nova_grade[i][j] = ESPALHADOR

            elif grade[i][j] == ESPALHADOR:
                nova_grade[i][j] = INATIVO

            elif grade[i][j] == INATIVO:
                nova_grade[i][j] = INATIVO

    return nova_grade


def contar_estados(grade):
    """
    Conta quantas células existem em cada estado.
    """
    contagem = {
        IGNORANTE: 0,
        ESPALHADOR: 0,
        INATIVO: 0
    }

    for linha in grade:
        for celula in linha:
            contagem[celula] += 1

    return contagem


def imprimir_grade(grade, limite=30):
    """
    Mostra parte da grade no terminal.
    Use apenas para grades pequenas ou para demonstração.
    """
    simbolos = {
        IGNORANTE: ".",
        ESPALHADOR: "E",
        INATIVO: "N"
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
    mostrar_grade=False
):
    """
    Executa a simulação sequencial completa.
    """

    grade = criar_grade(
        linhas,
        colunas,
        percentual_espalhadores
    )

    print("=== SIMULAÇÃO SEQUENCIAL DE PROPAGAÇÃO DE FAKE NEWS ===")
    print(f"Tamanho da grade: {linhas} x {colunas} ({linhas*colunas:,}) pessoas)")
    print(f"Gerações: {geracoes}")
    contagem_inicial = contar_estados(grade)
    print(
        f"Percentual inicial de espalhadores: "
        f"{percentual_espalhadores * 100:.2f}% "
        f"({contagem_inicial[ESPALHADOR]:,} espalhadores reais)"
    )
    print(f"Limiar de convencimento: {limiar_convencimento} vizinhos")
    print()

    inicio = time.time()

    for geracao in range(geracoes):
        grade = proxima_geracao(grade, limiar_convencimento)

        contagem = contar_estados(grade)

        print(
            f"Geração {geracao + 1:03d} | "
            f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
            f"Espalhadores: {contagem[ESPALHADOR]:>10,} | "
            f"Inativos: {contagem[INATIVO]:>10,}"
        )

        if mostrar_grade:
            imprimir_grade(grade)

        if contagem[ESPALHADOR] == 0:
            print("\nA propagação terminou: não há mais espalhadores.")
            break

    fim = time.time()

    tempo_total = fim - inicio

    print()
    print("=== RESULTADO FINAL ===")
    print(f"Tempo total de execução: {tempo_total:.4f} segundos")

    contagem_final = contar_estados(grade)
    total = linhas * colunas

    print(f"Ignorantes finais: {contagem_final[IGNORANTE]:,} ({contagem_final[IGNORANTE] / total * 100:,.2f}%)")
    print(f"Espalhadores finais: {contagem_final[ESPALHADOR]:,} ({contagem_final[ESPALHADOR] / total * 100:,.2f}%)")
    print(f"Inativos finais: {contagem_final[INATIVO]:,} ({contagem_final[INATIVO] / total * 100:,.2f}%)")


if __name__ == "__main__":
    executar_simulacao(
        linhas=100,
        colunas=100,
        geracoes=50,
        percentual_espalhadores=0.05,
        limiar_convencimento=3,
        mostrar_grade=False
    )