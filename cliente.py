import argparse
import socket
import struct
import time

# ---------------------------------------------------------------------------
# Importa utilitários do sequencial refatorado (M1)
# ---------------------------------------------------------------------------
from fakenews_sequencial import (
    IGNORANTE,
    ESPALHADOR_A,
    ESPALHADOR_B,
    INATIVO,
    contar_vizinhos_por_tipo,
    contar_vizinhos_espalhadores,
)

# ---------------------------------------------------------------------------
# Constantes do protocolo (devem coincidir com servidor.py)
# ---------------------------------------------------------------------------
HALO_COMPLETO = 0
NADA_MUDOU    = 1


# ---------------------------------------------------------------------------
# Funções de comunicação (espelho do servidor)
# ---------------------------------------------------------------------------

def enviar_tudo(conn: socket.socket, dados: bytes) -> None:
    """
    Envia todos os bytes de `dados` pela conexão.

    Parâmetros
    ----------
    conn : socket.socket
        Socket de conexão ativa.
    dados : bytes
        Dados a enviar.
    """
    conn.sendall(dados)


def receber_exato(conn: socket.socket, n: int) -> bytes:
    """
    Recebe exatamente `n` bytes da conexão.

    Parâmetros
    ----------
    conn : socket.socket
        Socket de conexão ativa.
    n : int
        Número exato de bytes a receber.

    Retorno
    -------
    bytes
        Exatamente `n` bytes recebidos.

    Exceções
    --------
    ConnectionError
        Se a conexão for encerrada antes de receber `n` bytes.
    """
    buffer = b""
    while len(buffer) < n:
        trecho = conn.recv(n - len(buffer))
        if not trecho:
            raise ConnectionError("Conexão encerrada prematuramente pelo servidor.")
        buffer += trecho
    return buffer


def desserializar_grade(dados: bytes, linhas: int, colunas: int) -> list:
    """
    Reconstrói uma grade a partir de bytes.

    Parâmetros
    ----------
    dados : bytes
        Bytes recebidos.
    linhas : int
        Número de linhas.
    colunas : int
        Número de colunas.

    Retorno
    -------
    list[list[int]]
        Grade reconstruída.
    """
    grade = []
    for i in range(linhas):
        inicio = i * colunas
        grade.append(list(dados[inicio: inicio + colunas]))
    return grade


def serializar_grade(grade: list) -> bytes:
    """
    Converte uma grade em bytes para transmissão.

    Parâmetros
    ----------
    grade : list[list[int]]
        Grade a serializar.

    Retorno
    -------
    bytes
        Representação binária da grade.
    """
    return bytes(celula for linha in grade for celula in linha)


def receber_halo(
    conn: socket.socket,
    halo_anterior: list,
    colunas: int,
) -> list:
    """
    Recebe uma linha halo do servidor, aplicando a otimização NADA_MUDOU.

    Se o servidor indicar NADA_MUDOU, retorna `halo_anterior` sem ler dados
    adicionais. Se indicar HALO_COMPLETO, lê e retorna a linha completa.

    Parâmetros
    ----------
    conn : socket.socket
        Conexão com o servidor.
    halo_anterior : list[int] ou None
        Halo recebido na geração anterior (None na primeira geração).
    colunas : int
        Número de colunas.

    Retorno
    -------
    list[int]
        Linha halo para uso nesta geração.
    """
    flag = receber_exato(conn, 1)[0]
    if flag == NADA_MUDOU:
        # Fronteira não mudou: reutiliza o halo anterior sem tráfego extra.
        return list(halo_anterior)
    else:
        dados = receber_exato(conn, colunas)
        return list(dados)


# ---------------------------------------------------------------------------
# Núcleo de processamento do escravo
# ---------------------------------------------------------------------------

def processar_fatia(
    fatia_com_halos: list,
    tem_halo_superior: bool,
    tem_halo_inferior: bool,
    limiar_convencimento: int,
    multiplas_noticias: bool,
) -> list:
    """
    Calcula a próxima geração para as linhas da fatia recebida.

    As linhas halo (primeira e/ou última linha) são usadas apenas para
    consulta de vizinhança — nunca são escritas no resultado.

    O processamento replica exatamente a lógica do sequencial (M1):
    - IGNORANTE → ESPALHADOR(_A/_B) se vizinhos >= limiar.
    - ESPALHADOR(_A/_B) → INATIVO.
    - INATIVO → INATIVO.

    Parâmetros
    ----------
    fatia_com_halos : list[list[int]]
        Fatia recebida incluindo as linhas halo (leitura apenas).
    tem_halo_superior : bool
        Indica se a primeira linha de `fatia_com_halos` é um halo (não processa).
    tem_halo_inferior : bool
        Indica se a última linha de `fatia_com_halos` é um halo (não processa).
    limiar_convencimento : int
        Mínimo de vizinhos espalhadores para converter um ignorante.
    multiplas_noticias : bool
        Ativa o modo competitivo A vs B.

    Retorno
    -------
    list[list[int]]
        Fatia processada (somente linhas reais, sem halos).
    """
    total_linhas = len(fatia_com_halos)
    colunas = len(fatia_com_halos[0]) if fatia_com_halos else 0

    # Índices das linhas reais dentro de fatia_com_halos.
    linha_real_inicio = 1 if tem_halo_superior else 0
    linha_real_fim    = total_linhas - (1 if tem_halo_inferior else 0)

    # Buffer de destino (apenas linhas reais).
    resultado = []

    for i in range(linha_real_inicio, linha_real_fim):
        linha_nova = []
        for j in range(colunas):
            estado = fatia_com_halos[i][j]

            if estado == IGNORANTE:
                if multiplas_noticias:
                    viz_a, viz_b = contar_vizinhos_por_tipo(fatia_com_halos, i, j)
                    total_viz = viz_a + viz_b
                    if total_viz >= limiar_convencimento:
                        if viz_a > viz_b:
                            linha_nova.append(ESPALHADOR_A)
                        elif viz_b > viz_a:
                            linha_nova.append(ESPALHADOR_B)
                        else:
                            linha_nova.append(IGNORANTE)  # Empate: permanece ignorante.
                    else:
                        linha_nova.append(IGNORANTE)
                else:
                    total_viz = contar_vizinhos_espalhadores(fatia_com_halos, i, j)
                    if total_viz >= limiar_convencimento:
                        linha_nova.append(ESPALHADOR_A)
                    else:
                        linha_nova.append(IGNORANTE)

            elif estado in (ESPALHADOR_A, ESPALHADOR_B):
                linha_nova.append(INATIVO)

            else:  # INATIVO
                linha_nova.append(INATIVO)

        resultado.append(linha_nova)

    return resultado


# ---------------------------------------------------------------------------
# Loop principal do escravo
# ---------------------------------------------------------------------------

def executar_cliente(
    host: str = "127.0.0.1",
    porta: int = 65432,
    id_escravo: int = 0,
) -> None:
    """
    Conecta ao servidor e executa o loop de processamento distribuído.

    O escravo fica em loop recebendo fatias + halos, processando e enviando
    resultados até o servidor enviar o sinal de encerramento (fatia com 0 linhas).

    Parâmetros
    ----------
    host : str
        Endereço IP ou hostname do servidor mestre.
    porta : int
        Porta de conexão com o servidor mestre.
    id_escravo : int
        Identificador numérico deste escravo (para logs).
    """
    print(f"[Escravo {id_escravo}] Conectando ao servidor {host}:{porta}...")

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Tenta conectar com retry (o servidor pode ainda não estar pronto).
    for tentativa in range(10):
        try:
            conn.connect((host, porta))
            break
        except ConnectionRefusedError:
            if tentativa == 9:
                raise RuntimeError(f"[Escravo {id_escravo}] Servidor não respondeu após 10 tentativas.")
            time.sleep(0.3)

    print(f"[Escravo {id_escravo}] Conectado.")

    # Recebe parâmetros globais: limiar (I), colunas (I), multiplas_noticias (?).
    dados_config = receber_exato(conn, struct.calcsize("!II?"))
    limiar_convencimento, colunas, multiplas_noticias = struct.unpack("!II?", dados_config)

    print(
        f"[Escravo {id_escravo}] Configuração recebida: "
        f"limiar={limiar_convencimento}, colunas={colunas}, "
        f"modo_competitivo={multiplas_noticias}"
    )

    # Halos anteriores para a otimização de fronteiras inteligentes.
    halo_sup_anterior = None
    halo_inf_anterior = None

    geracao = 0

    while True:
        # --- Recebe cabeçalho da fatia ---
        cabecalho = receber_exato(conn, struct.calcsize("!II"))
        linhas_fatia, colunas_recebidas = struct.unpack("!II", cabecalho)

        # Sinal de encerramento: servidor enviou fatia com 0 linhas.
        if linhas_fatia == 0:
            print(f"[Escravo {id_escravo}] Sinal de encerramento recebido. Encerrando.")
            break

        # --- Recebe corpo da fatia ---
        dados_fatia = receber_exato(conn, linhas_fatia * colunas_recebidas)
        fatia_com_halos = desserializar_grade(dados_fatia, linhas_fatia, colunas_recebidas)

        tem_halo_superior = False
        tem_halo_inferior = False

        # Lê flag do halo superior.
        flag_sup = receber_exato(conn, 1)[0]
        if flag_sup == HALO_COMPLETO:
            halo_sup = list(receber_exato(conn, colunas))
            halo_sup_anterior = halo_sup
            tem_halo_superior = True
        elif flag_sup == NADA_MUDOU and halo_sup_anterior is not None:
            halo_sup = list(halo_sup_anterior)
            tem_halo_superior = True
        else:
            halo_sup = None  # Primeira fatia: sem halo superior.

        # Lê flag do halo inferior.
        flag_inf = receber_exato(conn, 1)[0]
        if flag_inf == HALO_COMPLETO:
            halo_inf = list(receber_exato(conn, colunas))
            halo_inf_anterior = halo_inf
            tem_halo_inferior = True
        elif flag_inf == NADA_MUDOU and halo_inf_anterior is not None:
            halo_inf = list(halo_inf_anterior)
            tem_halo_inferior = True
        else:
            halo_inf = None  # Última fatia: sem halo inferior.

        # Reconstrói a fatia completa com halos nas posições corretas.
        fatia_final = []
        if halo_sup is not None:
            fatia_final.append(halo_sup)
        fatia_final.extend(fatia_com_halos)
        if halo_inf is not None:
            fatia_final.append(halo_inf)

        tem_halo_superior = halo_sup is not None
        tem_halo_inferior = halo_inf is not None

        # --- Processa a fatia ---
        resultado = processar_fatia(
            fatia_final,
            tem_halo_superior,
            tem_halo_inferior,
            limiar_convencimento,
            multiplas_noticias,
        )

        # --- Envia resultado ao servidor ---
        linhas_resultado = len(resultado)
        enviar_tudo(conn, struct.pack("!I", linhas_resultado))
        enviar_tudo(conn, serializar_grade(resultado))

        geracao += 1
        print(f"[Escravo {id_escravo}] Geração {geracao:03d} processada ({linhas_resultado} linhas).")

    conn.close()
    print(f"[Escravo {id_escravo}] Encerrado após {geracao} gerações.")


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def parse_argumentos():
    """Interpreta os argumentos de linha de comando do cliente escravo."""
    parser = argparse.ArgumentParser(
        description="Cliente escravo da simulação distribuída de propagação de fake news."
    )
    parser.add_argument("--host",  type=str, default="127.0.0.1", help="Endereço IP do servidor")
    parser.add_argument("--porta", type=int, default=65432,       help="Porta do servidor")
    parser.add_argument("--id",    type=int, default=0,           help="ID deste escravo (para logs)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_argumentos()
    executar_cliente(host=args.host, porta=args.porta, id_escravo=args.id)