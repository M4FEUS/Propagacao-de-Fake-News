"""
Simulação paralela de Propagação de Fake News usando Multiprocessing.
Uso:
    python fakenews_paralelo.py --linhas 200 --colunas 200 --geracoes 50 --processos 4

    # Com influenciadores digitais:
    python fakenews_paralelo.py --linhas 200 --colunas 200 --geracoes 50 \\
        --processos 4 --influenciadores 0.001

    # Testar múltiplas contagens de processos e registrar tempos:
    python fakenews_paralelo.py --linhas 500 --colunas 500 --geracoes 30 --benchmark


Este módulo implementa a simulação de propagação de fake news em uma grade bidimensional, paralelizando o cálculo de cada geração usando múltiplos processos.
"""

import argparse
import ctypes
import multiprocessing as mp
import random
import time

# ---------------------------------------------------------------------------
# Importa constantes e utilitários do sequencial (M1) — sem modificações.
# ---------------------------------------------------------------------------
from fakenews_sequencial import (
    IGNORANTE,
    ESPALHADOR_A,
    ESPALHADOR_B,
    ESPALHADOR,
    INATIVO,
    ESTADOS_ESPALHADORES,
    criar_grade,
    criar_grade_vazia,
    contar_estados,
    total_espalhadores_ativos,
    imprimir_grade,
)

# ---------------------------------------------------------------------------
# Constante adicional para influenciadores digitais (inovação M2)
# ---------------------------------------------------------------------------
INFLUENCIADOR = 4  # Super-nó: vizinhança estendida + maior poder de convencimento.

_SIMBOLOS_PARALELO = {
    IGNORANTE:    ".",
    ESPALHADOR:   "E",
    ESPALHADOR_A: "A",
    ESPALHADOR_B: "B",
    INATIVO:      "N",
    INFLUENCIADOR: "I",
}


# ---------------------------------------------------------------------------
# Conversão entre matriz (list[list[int]]) e vetor 1D de memória compartilhada
# ---------------------------------------------------------------------------

def matriz_para_array_compartilhado(grade):
    """
    Converte uma matriz (list[list[int]]) em um multiprocessing.Array 1D.

    O array compartilhado é necessário porque processos (diferente de
    threads) não compartilham o heap do interpretador: listas Python
    comuns NÃO seriam visíveis entre processos. `multiprocessing.Array`
    aloca um bloco de memória no nível do sistema operacional, mapeado em
    todos os processos filhos, permitindo leitura/escrita direta sem
    serialização a cada acesso.

    Parâmetros
    ----------
    grade : list[list[int]]
        Matriz de entrada.

    Retorno
    -------
    multiprocessing.sharedctypes.SynchronizedArray
        Vetor 1D em memória compartilhada (tipo ctypes 'i'), tamanho
        linhas * colunas, com grade[i][j] armazenado em i * colunas + j.
    """
    linhas = len(grade)
    colunas = len(grade[0]) if linhas > 0 else 0
    vetor = mp.Array(ctypes.c_int, linhas * colunas, lock=False)
    for i in range(linhas):
        base = i * colunas
        for j in range(colunas):
            vetor[base + j] = grade[i][j]
    return vetor


def array_compartilhado_para_matriz(vetor, linhas, colunas):
    """
    Converte um multiprocessing.Array 1D de volta para list[list[int]].

    Usado apenas para impressão/depuração e para o retorno final da função
    de simulação (a matriz devolvida ao chamador é uma cópia comum em
    Python, sem mais relação com a memória compartilhada).

    Parâmetros
    ----------
    vetor : multiprocessing.sharedctypes.SynchronizedArray
        Vetor 1D de onde os dados serão lidos.
    linhas : int
        Número de linhas da matriz de saída.
    colunas : int
        Número de colunas da matriz de saída.

    Retorno
    -------
    list[list[int]]
        Matriz reconstruída a partir do vetor.
    """
    return [
        [vetor[i * colunas + j] for j in range(colunas)]
        for i in range(linhas)
    ]


# ---------------------------------------------------------------------------
# Funções de vizinhança com raio variável (operam direto sobre o vetor 1D)
# ---------------------------------------------------------------------------

def contar_vizinhos_com_raio(vetor, linhas, colunas, i, j, raio=1):
    """
    Conta vizinhos espalhadores (qualquer tipo) em uma vizinhança quadrada de raio `raio`.

    Para raio=1, equivale à vizinhança de Moore (8 vizinhos).
    Para raio=2, cobre uma grade 5x5 ao redor da célula (24 vizinhos máx.).

    Opera diretamente sobre o vetor 1D em memória compartilhada (somente
    leitura), evitando reconstruir a matriz 2D a cada chamada.

    Parâmetros
    ----------
    vetor : multiprocessing.sharedctypes.SynchronizedArray
        Vetor 1D da geração atual (somente leitura).
    linhas : int
        Número total de linhas da grade.
    colunas : int
        Número total de colunas da grade.
    i : int
        Linha da célula central.
    j : int
        Coluna da célula central.
    raio : int
        Raio da vizinhança (padrão: 1 → Moore padrão).

    Retorno
    -------
    tuple[int, int]
        (vizinhos_tipo_a_ou_geral, vizinhos_tipo_b)
    """
    viz_a = 0
    viz_b = 0

    for di in range(-raio, raio + 1):
        for dj in range(-raio, raio + 1):
            if di == 0 and dj == 0:
                continue
            ni = i + di
            nj = j + dj
            if 0 <= ni < linhas and 0 <= nj < colunas:
                estado = vetor[ni * colunas + nj]
                if estado == ESPALHADOR_A or estado == ESPALHADOR:
                    viz_a += 1
                elif estado == ESPALHADOR_B:
                    viz_b += 1
                # Influenciador ativo conta como espalhador_A para fins de pressão.
                elif estado == INFLUENCIADOR:
                    viz_a += 1

    return viz_a, viz_b


def celula_tem_influenciador_proximo(vetor, linhas, colunas, i, j, raio=2):
    """
    Verifica se há algum INFLUENCIADOR dentro do raio informado da célula (i, j).

    Usado para aplicar o limiar reduzido de influenciadores digitais a ignorantes
    que estejam na vizinhança estendida de um super-nó.

    Parâmetros
    ----------
    vetor : multiprocessing.sharedctypes.SynchronizedArray
        Vetor 1D de leitura.
    linhas : int
        Número total de linhas da grade.
    colunas : int
        Número total de colunas da grade.
    i : int
        Linha da célula.
    j : int
        Coluna da célula.
    raio : int
        Raio de detecção do influenciador (padrão: 2 → 5x5).

    Retorno
    -------
    bool
        True se há ao menos um INFLUENCIADOR no raio.
    """
    for di in range(-raio, raio + 1):
        for dj in range(-raio, raio + 1):
            if di == 0 and dj == 0:
                continue
            ni = i + di
            nj = j + dj
            if 0 <= ni < linhas and 0 <= nj < colunas:
                if vetor[ni * colunas + nj] == INFLUENCIADOR:
                    return True
    return False


# ---------------------------------------------------------------------------
# Processamento paralelo de uma fatia horizontal (executado em cada PROCESSO)
# ---------------------------------------------------------------------------

def processar_fatia(
    vetor_atual,
    vetor_destino,
    linhas,
    colunas,
    linha_inicio,
    linha_fim,
    limiar_convencimento,
    multiplas_noticias,
    raio_influenciador,
    barrier,
):
    """
    Função executada por cada PROCESSO — calcula a próxima geração para as
    linhas [linha_inicio, linha_fim) lendo de `vetor_atual` e escrevendo em
    `vetor_destino`. Ambos são `multiprocessing.Array` em memória
    compartilhada entre os processos.

    Ausência de race conditions:
    - Leitura: sempre de `vetor_atual` (imutável durante a geração; nenhum
      processo escreve nele nesta rodada).
    - Escrita: somente nas posições correspondentes às linhas
      [linha_inicio, linha_fim) de `vetor_destino`. Cada fatia tem uma
      região de índices exclusiva (sem sobreposição), então processos
      distintos nunca escrevem na mesma posição do array compartilhado —
      por isso não é necessário lock nas células individuais.

    Sincronização:
    - Ao finalizar sua fatia, o processo aguarda na `barrier`. O processo
      principal só decide qual array é "atual" e qual é "destino" na
      próxima geração depois que TODOS os processos retornarem do
      `Process.join()`, que por sua vez só ocorre depois que todos
      passarem pela barreira — isso garante que nenhum processo comece a
      ler a geração seguinte antes de a geração atual estar 100% calculada
      por todos.

    Parâmetros
    ----------
    vetor_atual : multiprocessing.sharedctypes.SynchronizedArray
        Vetor 1D de leitura desta geração (compartilhado, somente leitura).
    vetor_destino : multiprocessing.sharedctypes.SynchronizedArray
        Vetor 1D de escrita (regiões de índice exclusivas por processo).
    linhas : int
        Número total de linhas da grade.
    colunas : int
        Número total de colunas da grade.
    linha_inicio : int
        Primeira linha (inclusive) desta fatia.
    linha_fim : int
        Última linha (exclusiva) desta fatia.
    limiar_convencimento : int
        Mínimo de vizinhos espalhadores para converter um ignorante.
    multiplas_noticias : bool
        Ativa o modo competitivo A vs B.
    raio_influenciador : int
        Raio de vizinhança dos influenciadores digitais (0 = inovação desativada).
    barrier : multiprocessing.Barrier
        Barreira de sincronização entre gerações (compartilhada por todos
        os processos desta geração).
    """
    influenciadores_ativos = raio_influenciador > 0

    for i in range(linha_inicio, linha_fim):
        base = i * colunas
        for j in range(colunas):
            estado = vetor_atual[base + j]

            if estado == IGNORANTE:
                # Determina o limiar efetivo (reduzido se há influenciador próximo).
                if influenciadores_ativos and celula_tem_influenciador_proximo(
                    vetor_atual, linhas, colunas, i, j, raio_influenciador
                ):
                    # Influenciador reduz o limiar à metade (mínimo 1).
                    limiar_efetivo = max(1, limiar_convencimento // 2)
                    raio_busca = raio_influenciador
                else:
                    limiar_efetivo = limiar_convencimento
                    raio_busca = 1  # Vizinhança de Moore padrão.

                if multiplas_noticias:
                    viz_a, viz_b = contar_vizinhos_com_raio(
                        vetor_atual, linhas, colunas, i, j, raio_busca
                    )
                    total_viz = viz_a + viz_b
                    if total_viz >= limiar_efetivo:
                        if viz_a > viz_b:
                            vetor_destino[base + j] = ESPALHADOR_A
                        elif viz_b > viz_a:
                            vetor_destino[base + j] = ESPALHADOR_B
                        else:
                            vetor_destino[base + j] = IGNORANTE  # Empate.
                    else:
                        vetor_destino[base + j] = IGNORANTE
                else:
                    viz_a, _ = contar_vizinhos_com_raio(
                        vetor_atual, linhas, colunas, i, j, raio_busca
                    )
                    if viz_a >= limiar_efetivo:
                        vetor_destino[base + j] = ESPALHADOR_A
                    else:
                        vetor_destino[base + j] = IGNORANTE

            elif estado in ESTADOS_ESPALHADORES or estado == ESPALHADOR:
                # Espalhador vira inativo na próxima geração.
                vetor_destino[base + j] = INATIVO

            elif estado == INFLUENCIADOR:
                # Influenciador permanece ativo para sempre (super-nó persistente).
                vetor_destino[base + j] = INFLUENCIADOR

            else:
                # INATIVO: estado absorvente.
                vetor_destino[base + j] = INATIVO

    # Aguarda todos os processos terminarem antes que o coordenador troque os buffers.
    barrier.wait()


# ---------------------------------------------------------------------------
# Geração e gerenciamento de influenciadores digitais
# ---------------------------------------------------------------------------

def inserir_influenciadores(grade, percentual, semente_offset=1000):
    """
    Marca aleatoriamente algumas células como INFLUENCIADOR.

    Células que já são espalhadoras não são substituídas; apenas ignorantes
    são convertidos em influenciadores (super-nós inicialmente ativos).

    Parâmetros
    ----------
    grade : list[list[int]]
        Grade já inicializada (modifica in-place).
    percentual : float
        Fração da população a ser marcada como influenciador (ex.: 0.001 = 0,1%).
    semente_offset : int
        Offset somado à semente original para não interferir na grade base.

    Retorno
    -------
    int
        Quantidade de influenciadores efetivamente inseridos.
    """
    linhas = len(grade)
    colunas = len(grade[0])
    total = int(linhas * colunas * percentual)

    # Usa estado separado do gerador para não alterar a sequência do sequencial.
    rng = random.Random(semente_offset)

    inseridos = 0
    tentativas = 0
    max_tentativas = total * 10  # Evita loop infinito em grades densas.

    while inseridos < total and tentativas < max_tentativas:
        i = rng.randint(0, linhas - 1)
        j = rng.randint(0, colunas - 1)
        if grade[i][j] == IGNORANTE:
            grade[i][j] = INFLUENCIADOR
            inseridos += 1
        tentativas += 1

    return inseridos


# ---------------------------------------------------------------------------
# Divisão balanceada de fatias
# ---------------------------------------------------------------------------

def dividir_fatias(total_linhas, num_processos):
    """
    Divide `total_linhas` em `num_processos` fatias horizontais balanceadas.

    Linhas excedentes (total_linhas % num_processos) são distribuídas uma a
    uma pelas primeiras fatias, garantindo diferença máxima de 1 linha entre
    fatias.

    Parâmetros
    ----------
    total_linhas : int
        Número total de linhas da grade.
    num_processos : int
        Número de processos (e fatias).

    Retorno
    -------
    list[tuple[int, int]]
        Lista de tuplas (inicio, fim) onde fim é exclusivo.
    """
    base = total_linhas // num_processos
    resto = total_linhas % num_processos
    fatias = []
    inicio = 0
    for i in range(num_processos):
        tam = base + (1 if i < resto else 0)
        fatias.append((inicio, inicio + tam))
        inicio += tam
    return fatias


# ---------------------------------------------------------------------------
# Execução paralela principal
# ---------------------------------------------------------------------------

def executar_simulacao_paralela(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    limiar_convencimento=2,
    num_processos=4,
    semente=42,
    mostrar_grade=False,
    multiplas_noticias=False,
    percentual_influenciadores=0.0,
    raio_influenciador=2,
    silencioso=False,
):
    """
    Executa a simulação paralela com double buffering e barreira entre gerações.

    Cada geração:
    1. N processos calculam fatias horizontais em paralelo lendo do array
       compartilhado "atual".
    2. Cada processo escreve somente na sua região de índices do array
       compartilhado "destino" (sem locks de célula).
    3. Todos os processos aguardam na `barrier` antes de retornar.
    4. O processo coordenador (principal) faz `join()` em todos e então
       troca as referências atual/destino, avançando para a próxima
       geração.

    Parâmetros
    ----------
    linhas : int
        Número de linhas da grade.
    colunas : int
        Número de colunas da grade.
    geracoes : int
        Número máximo de gerações.
    percentual_espalhadores : float
        Fração inicial de espalhadores.
    limiar_convencimento : int
        Vizinhos espalhadores para converter um ignorante.
    num_processos : int
        Número de processos de processamento (deve ser >= 1).
    semente : int ou None
        Semente aleatória para reprodutibilidade.
    mostrar_grade : bool
        Imprime a grade após cada geração (útil para grades pequenas).
    multiplas_noticias : bool
        Ativa o modo competitivo A vs B (herda lógica do sequencial M1).
    percentual_influenciadores : float
        Fração de influenciadores digitais inseridos (0.0 = inovação desativada).
    raio_influenciador : int
        Raio da vizinhança estendida dos influenciadores (padrão: 2 → 5x5).
    silencioso : bool
        Suprime saída por geração (útil para benchmarks).

    Retorno
    -------
    tuple[list[list[int]], float]
        (grade_final, tempo_total_segundos)
    """
    # Garante que o número de processos não exceda o número de linhas.
    num_processos = min(num_processos, linhas)

    # ---- Inicialização da grade (lista comum, na memória do processo principal) ----
    grade_a = criar_grade(
        linhas, colunas, percentual_espalhadores, semente, multiplas_noticias
    )

    # Insere influenciadores digitais, se configurado (antes de migrar para a memória compartilhada).
    num_influenciadores = 0
    if percentual_influenciadores > 0:
        num_influenciadores = inserir_influenciadores(
            grade_a, percentual_influenciadores, semente_offset=(semente or 0) + 1000
        )

    # ---- Migra a grade para memória compartilhada entre processos ----
    # multiprocessing.Array é necessário aqui: diferente de threads, os
    # processos filhos não veem as listas Python do processo principal.
    vetor_a = matriz_para_array_compartilhado(grade_a)
    vetor_b = mp.Array(ctypes.c_int, linhas * colunas, lock=False)  # buffer destino, começa zerado

    # ---- Divisão de fatias ----
    fatias = dividir_fatias(linhas, num_processos)

    if not silencioso:
        titulo = (
            "=== SIMULAÇÃO PARALELA — FAKE NEWS (A vs B) ==="
            if multiplas_noticias
            else "=== SIMULAÇÃO PARALELA DE PROPAGAÇÃO DE FAKE NEWS ==="
        )
        print(titulo)
        print(f"Grade: {linhas}x{colunas} ({linhas*colunas:,} pessoas)")
        print(f"Gerações: {geracoes} | Processos: {num_processos} | Semente: {semente}")
        print(f"Espalhadores iniciais: {percentual_espalhadores*100:.2f}%")
        print(f"Limiar de convencimento: {limiar_convencimento} vizinhos")
        if num_influenciadores > 0:
            print(
                f"Influenciadores digitais: {num_influenciadores:,} "
                f"({percentual_influenciadores*100:.3f}%) | "
                f"Raio: {raio_influenciador} → vizinhança {2*raio_influenciador+1}x{2*raio_influenciador+1}"
            )
        print(f"Fatias: {[(li, lf) for li, lf in fatias]}")
        print("Mecanismo: multiprocessing.Process + multiprocessing.Array + multiprocessing.Barrier")
        print()

    inicio = time.time()

    for geracao in range(geracoes):
        # Barreira: num_processos workers. O processo coordenador (principal)
        # Não entra na barreira como worker; ele apenas aguarda os join()
        # retornarem antes de trocar os buffers.
        barrier = mp.Barrier(num_processos)

        processos = []
        for linha_inicio, linha_fim in fatias:
            p = mp.Process(
                target=processar_fatia,
                args=(
                    vetor_a,      # Leitura — imutável durante a geração.
                    vetor_b,      # Escrita — região de índices exclusiva deste processo.
                    linhas,
                    colunas,
                    linha_inicio,
                    linha_fim,
                    limiar_convencimento,
                    multiplas_noticias,
                    raio_influenciador if percentual_influenciadores > 0 else 0,
                    barrier,
                ),
                daemon=True,
            )
            processos.append(p)

        # Inicia todos os processos simultaneamente.
        for p in processos:
            p.start()

        # Aguarda todos os processos concluírem (passarem pela barreira e encerrarem).
        for p in processos:
            p.join()

        # Troca os buffers: vetor_b (resultado) passa a ser o vetor atual.
        vetor_a, vetor_b = vetor_b, vetor_a

        # ---- Estatísticas da geração ----
        # Reconstrói a matriz 2D somente para contagem/impressão (não afeta
        # o vetor compartilhado usado pelos processos).
        grade_atual = array_compartilhado_para_matriz(vetor_a, linhas, colunas)
        contagem = contar_estados(grade_atual)

        if not silencioso:
            esp_a = contagem.get(ESPALHADOR_A, 0) + contagem.get(ESPALHADOR, 0)
            esp_b = contagem.get(ESPALHADOR_B, 0)
            if multiplas_noticias:
                print(
                    f"Geração {geracao + 1:03d} | "
                    f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
                    f"Esp. A: {esp_a:>8,} | "
                    f"Esp. B: {esp_b:>8,} | "
                    f"Inativos: {contagem[INATIVO]:>10,} | "
                    f"Influenc.: {contagem.get(INFLUENCIADOR, 0):>6,}"
                )
            else:
                print(
                    f"Geração {geracao + 1:03d} | "
                    f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
                    f"Espalhadores: {esp_a:>10,} | "
                    f"Inativos: {contagem[INATIVO]:>10,} | "
                    f"Influenc.: {contagem.get(INFLUENCIADOR, 0):>6,}"
                )

            if mostrar_grade:
                _imprimir_grade_paralela(grade_atual)

        # Parada antecipada: sem espalhadores ativos (influenciadores não contam).
        esp_ativos = total_espalhadores_ativos(contagem)
        if esp_ativos == 0:
            if not silencioso:
                print("\nA propagação terminou: não há mais espalhadores.")
            break

    fim = time.time()
    tempo_total = fim - inicio

    grade_final = array_compartilhado_para_matriz(vetor_a, linhas, colunas)

    if not silencioso:
        print()
        print("=== RESULTADO FINAL ===")
        print(f"Tempo total de execução: {tempo_total:.4f} segundos")
        contagem_f = contar_estados(grade_final)
        total_celulas = linhas * colunas
        print(
            f"Ignorantes finais:   {contagem_f[IGNORANTE]:,} "
            f"({contagem_f[IGNORANTE]/total_celulas*100:.2f}%)"
        )
        esp_final = (
            contagem_f.get(ESPALHADOR_A, 0)
            + contagem_f.get(ESPALHADOR_B, 0)
            + contagem_f.get(ESPALHADOR, 0)
        )
        print(f"Espalhadores finais: {esp_final:,} ({esp_final/total_celulas*100:.2f}%)")
        print(
            f"Inativos finais:     {contagem_f[INATIVO]:,} "
            f"({contagem_f[INATIVO]/total_celulas*100:.2f}%)"
        )
        if num_influenciadores > 0:
            print(f"Influenciadores:     {contagem_f.get(INFLUENCIADOR, 0):,} (persistentes)")

    return grade_final, tempo_total


# ---------------------------------------------------------------------------
# Modo benchmark: testa 1, 2, 4, 8 processos e exibe tabela de speedup
# ---------------------------------------------------------------------------

def executar_benchmark(
    linhas=500,
    colunas=500,
    geracoes=30,
    percentual_espalhadores=0.05,
    limiar_convencimento=2,
    semente=42,
    lista_processos=(1, 2, 4, 8),
):
    """
    Executa a simulação com diferentes contagens de processos e exibe speedup/eficiência.

    Parâmetros
    ----------
    linhas, colunas : int
        Dimensões da grade.
    geracoes : int
        Gerações por execução.
    percentual_espalhadores : float
        Fração inicial de espalhadores.
    limiar_convencimento : int
        Limiar de conversão.
    semente : int
        Semente aleatória.
    lista_processos : tuple[int]
        Sequência de contagens de processos a testar.
    """
    print("=" * 65)
    print("BENCHMARK PARALELO (MULTIPROCESSING) — PROPAGAÇÃO DE FAKE NEWS")
    print(f"Grade: {linhas}x{colunas} | Gerações: {geracoes} | Semente: {semente}")
    print("=" * 65)

    tempos = {}
    for n in lista_processos:
        print(f"\n[Processos: {n}] Executando...", end=" ", flush=True)
        _, tempo = executar_simulacao_paralela(
            linhas=linhas,
            colunas=colunas,
            geracoes=geracoes,
            percentual_espalhadores=percentual_espalhadores,
            limiar_convencimento=limiar_convencimento,
            num_processos=n,
            semente=semente,
            silencioso=True,
        )
        tempos[n] = tempo
        print(f"{tempo:.4f}s")

    # Tempo de referência: 1 processo (equivale ao sequencial paralelizado).
    t_ref = tempos.get(1, tempos[min(tempos)])

    print()
    print(f"{'Processos':>9} | {'Tempo (s)':>10} | {'Speedup':>8} | {'Eficiência':>10}")
    print("-" * 47)
    for n, t in sorted(tempos.items()):
        speedup = t_ref / t
        eficiencia = speedup / n * 100
        print(f"{n:>9} | {t:>10.4f} | {speedup:>8.3f} | {eficiencia:>9.1f}%")

    print()
    print("Speedup S = T(1) / T(N) | Eficiência E = S / N × 100%")


# ---------------------------------------------------------------------------
# Utilitário: impressão da grade com símbolo de influenciador
# ---------------------------------------------------------------------------

def _imprimir_grade_paralela(grade, limite=30):
    """Imprime a grade incluindo o símbolo 'I' para influenciadores."""
    linhas = min(len(grade), limite)
    colunas = min(len(grade[0]), limite) if grade else 0
    for i in range(linhas):
        linha = ""
        for j in range(colunas):
            linha += _SIMBOLOS_PARALELO.get(grade[i][j], "?") + " "
        print(linha)
    print()


# ---------------------------------------------------------------------------
# Interface de linha de comando
# ---------------------------------------------------------------------------

def parse_argumentos():
    """
    Define e interpreta os argumentos de linha de comando.

    Retorno
    -------
    argparse.Namespace
        Parâmetros da simulação paralela.
    """
    parser = argparse.ArgumentParser(
        description="Simulação paralela de propagação de fake news com Multiprocessing."
    )
    parser.add_argument("--linhas",      type=int,   default=100,  help="Linhas da grade (padrão: 100)")
    parser.add_argument("--colunas",     type=int,   default=100,  help="Colunas da grade (padrão: 100)")
    parser.add_argument("--geracoes",    type=int,   default=50,   help="Gerações máximas (padrão: 50)")
    parser.add_argument("--espalhadores",type=float, default=0.02, help="%% inicial espalhadores (padrão: 0.02)")
    parser.add_argument("--semente",     type=int,   default=42,   help="Semente aleatória (padrão: 42)")
    parser.add_argument("--limiar",      type=int,   default=2,    help="Limiar de convencimento (padrão: 2)")
    parser.add_argument("--processos",   type=int,   default=4,    help="Número de processos (padrão: 4)")
    parser.add_argument(
        "--mostrar-grade", action="store_true",
        help="Imprime a grade a cada geração (grades pequenas)"
    )
    parser.add_argument(
        "--multiplas-noticias", action="store_true",
        help="Modo competitivo A vs B (herda lógica do sequencial M1)"
    )
    parser.add_argument(
        "--influenciadores", type=float, default=0.0,
        help="Percentual de influenciadores digitais, ex.: 0.001 (padrão: 0 = desativado)"
    )
    parser.add_argument(
        "--raio-influenciador", type=int, default=2,
        help="Raio da vizinhança dos influenciadores (padrão: 2 → 5x5)"
    )
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Executa benchmark com 1, 2, 4, 8 processos e exibe tabela de speedup"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Necessário no Windows e macOS (método de início "spawn"), e inofensivo
    # no Linux ("fork"): garante que os processos filhos sejam criados de
    # forma segura ao executar este módulo como script principal.
    mp.freeze_support()

    args = parse_argumentos()

    semente_valida = args.semente if args.semente >= 0 else None

    if args.benchmark:
        executar_benchmark(
            linhas=args.linhas,
            colunas=args.colunas,
            geracoes=args.geracoes,
            percentual_espalhadores=args.espalhadores,
            limiar_convencimento=args.limiar,
            semente=semente_valida,
        )
    else:
        executar_simulacao_paralela(
            linhas=args.linhas,
            colunas=args.colunas,
            geracoes=args.geracoes,
            percentual_espalhadores=args.espalhadores,
            limiar_convencimento=args.limiar,
            num_processos=args.processos,
            semente=semente_valida,
            mostrar_grade=args.mostrar_grade,
            multiplas_noticias=args.multiplas_noticias,
            percentual_influenciadores=args.influenciadores,
            raio_influenciador=args.raio_influenciador,
        )
