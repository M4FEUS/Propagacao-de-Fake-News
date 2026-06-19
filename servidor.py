"""
Uso:
   # Terminal 1 — iniciar o servidor:
   python servidor.py --linhas 100 --colunas 100 --geracoes 50 --clientes 2

   # Terminais 2 e 3 — iniciar os clientes:
   python cliente.py --host 127.0.0.1 --porta 65432 --id 0
   python cliente.py --host 127.0.0.1 --porta 65433 --id 1

   # Ou tudo automaticamente na mesma máquina:
   python servidor.py --linhas 100 --colunas 100 --geracoes 50 --clientes 2 --auto
"""

import argparse
import socket
import struct
import subprocess
import sys
import time

from fakenews_sequencial import (
    IGNORANTE,
    ESPALHADOR_A,
    ESPALHADOR_B,
    INATIVO,
    criar_grade,
    criar_grade_vazia,
    contar_estados,
    total_espalhadores_ativos,
)

# ---------------------------------------------------------------------------
# Constantes de protocolo
# ---------------------------------------------------------------------------
HALO_COMPLETO = 0   # A linha halo segue imediatamente após este byte.
NADA_MUDOU    = 1   # Linha halo idêntica à anterior; escravo reutiliza.
SEM_HALO      = 2   # Esta borda não tem vizinho (primeira/última fatia).

PORTA_BASE = 65432
BACKLOG    = 1


# ---------------------------------------------------------------------------
# Serialização / Desserialização
# ---------------------------------------------------------------------------

def serializar_grade(grade):
    """Converte lista de listas em bytes (1 byte por célula)."""
    return bytes(c for linha in grade for c in linha)


def desserializar_grade(dados, linhas, colunas):
    """Reconstrói lista de listas a partir de bytes recebidos."""
    return [list(dados[i*colunas:(i+1)*colunas]) for i in range(linhas)]


# ---------------------------------------------------------------------------
# Comunicação confiável
# ---------------------------------------------------------------------------

def enviar_tudo(conn, dados):
    """Garante que todos os bytes sejam enviados."""
    conn.sendall(dados)


def receber_exato(conn, n):
    """Bloqueia até receber exatamente n bytes."""
    buf = b""
    while len(buf) < n:
        trecho = conn.recv(n - len(buf))
        if not trecho:
            raise ConnectionError("Conexão encerrada antes de receber todos os dados.")
        buf += trecho
    return buf


# ---------------------------------------------------------------------------
# Halo exchange com Fronteiras Inteligentes
# ---------------------------------------------------------------------------

def enviar_halo(conn, linha_atual, linha_anterior, colunas):
    """
    Envia uma linha halo ao escravo com a otimização de fronteira inteligente.

    Compara `linha_atual` com `linha_anterior`:
    - Se idênticas, envia apenas NADA_MUDOU (1 byte) — economia de `colunas` bytes.
    - Se diferentes ou primeira geração (anterior == None), envia HALO_COMPLETO + linha.

    Parâmetros
    ----------
    conn : socket.socket
    linha_atual : list[int]  — linha halo desta geração.
    linha_anterior : list[int] | None — linha halo da geração anterior.
    colunas : int
    """
    if linha_anterior is not None and linha_atual == linha_anterior:
        enviar_tudo(conn, bytes([NADA_MUDOU]))
    else:
        enviar_tudo(conn, bytes([HALO_COMPLETO]))
        enviar_tudo(conn, bytes(linha_atual))


# ---------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------

def dividir_grade(total_linhas, num_clientes):
    """
    Divide `total_linhas` em `num_clientes` fatias balanceadas.

    Retorno: lista de tuplas (inicio, fim) onde fim é exclusivo.
    Linhas excedentes são distribuídas uma a uma pelas primeiras fatias.
    """
    base  = total_linhas // num_clientes
    resto = total_linhas % num_clientes
    fatias, inicio = [], 0
    for i in range(num_clientes):
        tam = base + (1 if i < resto else 0)
        fatias.append((inicio, inicio + tam))
        inicio += tam
    return fatias


def aceitar_clientes(num_clientes, porta_base):
    servidores, conexoes = [], []
    for i in range(num_clientes):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", porta_base + i))
        srv.listen(BACKLOG)
        print(f"  [Servidor] Aguardando escravo {i} na porta {porta_base + i}...")
        servidores.append(srv)

    for i, srv in enumerate(servidores):
        conn, addr = srv.accept()
        print(f"  [Servidor] Escravo {i} conectado: {addr}")
        conexoes.append(conn)
        srv.close()

    return conexoes


def executar_servidor(
    linhas=100,
    colunas=100,
    geracoes=50,
    percentual_espalhadores=0.02,
    limiar_convencimento=2,
    semente=42,
    num_clientes=2,
    porta_base=PORTA_BASE,
    multiplas_noticias=False,
):

    print("=== SERVIDOR MESTRE — PROPAGAÇÃO DE FAKE NEWS DISTRIBUÍDA ===")
    print(f"Grade: {linhas}x{colunas} | Gerações: {geracoes} | Escravos: {num_clientes}")
    print(f"Espalhadores: {percentual_espalhadores*100:.1f}% | Limiar: {limiar_convencimento} | Semente: {semente}")
    print()

    # Cria a grade inicial (mesma lógica do sequencial).
    grade = criar_grade(linhas, colunas, percentual_espalhadores, semente, multiplas_noticias)
    fatias_idx = dividir_grade(linhas, num_clientes)

    # Aceita conexões de todos os escravos.
    print("[Servidor] Aguardando conexão dos escravos...")
    conexoes = aceitar_clientes(num_clientes, porta_base)
    print(f"[Servidor] Todos os {num_clientes} escravos conectados.\n")

    # Envia parâmetros globais para cada escravo.
    config = struct.pack("!II?", limiar_convencimento, colunas, multiplas_noticias)
    for conn in conexoes:
        enviar_tudo(conn, config)

    # Histórico de halos para a otimização de fronteiras inteligentes.
    # Chaves: (id_escravo, "sup") e (id_escravo, "inf").
    halos_ant = {}

    inicio = time.time()
    bytes_economizados = 0  # Métrica da inovação de fronteiras inteligentes.

    for geracao in range(geracoes):
        nova_grade = criar_grade_vazia(linhas, colunas)

        # ---- Fase 1: envio de fatias + halos --------------------------------
        for idx, (li, lf) in enumerate(fatias_idx):
            conn      = conexoes[idx]
            fatia_real = grade[li:lf]
            n_linhas   = lf - li

            # Cabeçalho: linhas reais + colunas.
            enviar_tudo(conn, struct.pack("!II", n_linhas, colunas))
            # Corpo: fatia real serializada.
            enviar_tudo(conn, serializar_grade(fatia_real))

            # Halo superior (linha acima da fatia, se existir).
            if li > 0:
                linha_sup     = grade[li - 1]
                anterior_sup  = halos_ant.get((idx, "sup"))
                if anterior_sup is not None and linha_sup == anterior_sup:
                    enviar_tudo(conn, bytes([NADA_MUDOU]))
                    bytes_economizados += colunas
                else:
                    enviar_tudo(conn, bytes([HALO_COMPLETO]))
                    enviar_tudo(conn, bytes(linha_sup))
                halos_ant[(idx, "sup")] = list(linha_sup)
            else:
                enviar_tudo(conn, bytes([SEM_HALO]))  # Primeira fatia: sem halo superior.

            # Halo inferior (linha abaixo da fatia, se existir).
            if lf < linhas:
                linha_inf     = grade[lf]
                anterior_inf  = halos_ant.get((idx, "inf"))
                if anterior_inf is not None and linha_inf == anterior_inf:
                    enviar_tudo(conn, bytes([NADA_MUDOU]))
                    bytes_economizados += colunas
                else:
                    enviar_tudo(conn, bytes([HALO_COMPLETO]))
                    enviar_tudo(conn, bytes(linha_inf))
                halos_ant[(idx, "inf")] = list(linha_inf)
            else:
                enviar_tudo(conn, bytes([SEM_HALO]))  # Última fatia: sem halo inferior.

        # ---- Fase 2: coleta dos resultados ----------------------------------
        for idx, (li, lf) in enumerate(fatias_idx):
            conn       = conexoes[idx]
            n_esperado = lf - li

            # Cabeçalho: número de linhas do resultado.
            (n_resultado,) = struct.unpack("!I", receber_exato(conn, 4))
            if n_resultado != n_esperado:
                raise ValueError(
                    f"Escravo {idx} retornou {n_resultado} linhas; esperava {n_esperado}."
                )

            # Corpo: resultado processado.
            dados = receber_exato(conn, n_resultado * colunas)
            resultado = desserializar_grade(dados, n_resultado, colunas)
            for r, linha in enumerate(resultado):
                nova_grade[li + r] = linha

        grade = nova_grade

        # ---- Estatísticas da geração ----------------------------------------
        contagem = contar_estados(grade)
        n_esp = contagem.get(ESPALHADOR_A, 0) + contagem.get(ESPALHADOR_B, 0)
        print(
            f"Geração {geracao + 1:03d} | "
            f"Ignorantes: {contagem[IGNORANTE]:>10,} | "
            f"Espalhadores: {n_esp:>10,} | "
            f"Inativos: {contagem[INATIVO]:>10,} | "
            f"Bytes economizados: {bytes_economizados:,}"
        )

        # ---- Parada antecipada ----------------------------------------------
        if total_espalhadores_ativos(contagem) == 0:
            print("\n[Servidor] Propagação encerrada: nenhum espalhador ativo.")
            break

    fim = time.time()

    # Sinaliza encerramento (fatia com 0 linhas) para todos os escravos.
    sinal_fim = struct.pack("!II", 0, 0)
    for conn in conexoes:
        enviar_tudo(conn, sinal_fim)
        conn.close()

    # Resultado final.
    print()
    print("=== RESULTADO FINAL ===")
    print(f"Tempo total de execução:      {fim - inicio:.4f} segundos")
    print(f"Bytes economizados (halos):   {bytes_economizados:,}")
    contagem_f = contar_estados(grade)
    total = linhas * colunas
    print(f"Ignorantes finais:   {contagem_f[IGNORANTE]:,} ({contagem_f[IGNORANTE]/total*100:.2f}%)")
    print(f"Espalhadores finais: {contagem_f.get(ESPALHADOR_A,0)+contagem_f.get(ESPALHADOR_B,0):,}")
    print(f"Inativos finais:     {contagem_f[INATIVO]:,} ({contagem_f[INATIVO]/total*100:.2f}%)")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def parse_argumentos():
    p = argparse.ArgumentParser(
        description="Servidor mestre da simulação distribuída de propagação de fake news."
    )
    p.add_argument("--linhas",       type=int,   default=100,       help="Linhas da grade")
    p.add_argument("--colunas",      type=int,   default=100,       help="Colunas da grade")
    p.add_argument("--geracoes",     type=int,   default=50,        help="Gerações máximas")
    p.add_argument("--espalhadores", type=float, default=0.02,      help="Percentual inicial (0–1)")
    p.add_argument("--limiar",       type=int,   default=2,         help="Limiar de convencimento")
    p.add_argument("--semente",      type=int,   default=42,        help="Semente aleatória")
    p.add_argument("--clientes",     type=int,   default=2,         help="Número de escravos")
    p.add_argument("--porta",        type=int,   default=PORTA_BASE,help="Porta base")
    p.add_argument("--multiplas-noticias", action="store_true",     help="Modo competitivo A vs B")
    p.add_argument("--auto",         action="store_true",           help="Inicia clientes automaticamente")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_argumentos()

    if args.auto:
        processos = []
        for i in range(args.clientes):
            cmd = [
                sys.executable, "cliente.py",
                "--host", "127.0.0.1",
                "--porta", str(args.porta + i),
                "--id", str(i),
            ]
            processos.append(subprocess.Popen(cmd))

    executar_servidor(
        linhas=args.linhas,
        colunas=args.colunas,
        geracoes=args.geracoes,
        percentual_espalhadores=args.espalhadores,
        limiar_convencimento=args.limiar,
        semente=args.semente,
        num_clientes=args.clientes,
        porta_base=args.porta,
        multiplas_noticias=args.multiplas_noticias,
    )

    if args.auto:
        for p in processos:
            p.wait()