import subprocess
import time
import csv
import re

def extrair_tempo(output):
    """Procura no log do terminal o tempo total de execução gerado pelo script."""
    match = re.search(r"Tempo total de execução:\s+([0-9\.]+)\s+segundos", output)
    if match:
        return float(match.group(1))
    return None

def rodar_benchmark():
    # Cenários de carga de trabalho exigidos no roteiro
    tamanhos_matriz = [100, 500, 1000]
    num_processos = [1, 2, 4, 8]
    
    # Fixando alguns parâmetros para a bateria de testes
    geracoes = "50"
    espalhadores = "0.05"
    
    cenarios = []

    print("=== INICIANDO PIPELINE DE BENCHMARK ===")

    for tam in tamanhos_matriz:
        # -------------------------------------------------------------
        # 1. Executa a versão Sequencial (Nossa Baseline)
        # -------------------------------------------------------------
        cmd_seq = [
            "python", "fakenews_sequencial.py",
            "--linhas", str(tam),
            "--colunas", str(tam),
            "--geracoes", geracoes,
            "--espalhadores", espalhadores,
            "--multiplas-noticias"  # Garante que a sua inovação (Agências) esteja rodando
        ]
        
        print(f"\n[Sequencial] Matriz {tam}x{tam}...")
        inicio = time.time()
        res_seq = subprocess.run(cmd_seq, capture_output=True, text=True)
        
        tempo_seq = extrair_tempo(res_seq.stdout)
        if not tempo_seq:
            tempo_seq = time.time() - inicio
            
        cenarios.append({
            "Versao": "Sequencial",
            "Tamanho": f"{tam}x{tam}",
            "Processos": 1,
            "Tempo_Segundos": round(tempo_seq, 4)
        })
        print(f" -> Concluído em {tempo_seq:.4f}s")

        # -------------------------------------------------------------
        # 2. Executa a versão Paralela (Multiprocessing do M2)
        # -------------------------------------------------------------
        for p in num_processos:
            cmd_par = [
                "python", "fakenews_paralelo.py",
                "--linhas", str(tam),
                "--colunas", str(tam),
                "--geracoes", geracoes,
                "--espalhadores", espalhadores,
                "--multiplas-noticias",
                "--processos", str(p)  # Argumento crucial que o M2 precisa implementar
            ]
            
            print(f"[Paralela] Matriz {tam}x{tam} com {p} processo(s)...")
            inicio = time.time()
            res_par = subprocess.run(cmd_par, capture_output=True, text=True)
            
            # Validação de segurança: se o M2 ainda não criou o arquivo ou o script quebrar
            if res_par.returncode != 0:
                print(f" -> ERRO: O script falhou ou 'fakenews_paralelo.py' não foi encontrado.")
                print(f"Detalhe do erro: {res_par.stderr.strip().splitlines()[-1] if res_par.stderr else 'Desconhecido'}")
                continue
            
            tempo_par = extrair_tempo(res_par.stdout)
            if not tempo_par:
                tempo_par = time.time() - inicio
                
            cenarios.append({
                "Versao": "Paralela",
                "Tamanho": f"{tam}x{tam}",
                "Processos": p,
                "Tempo_Segundos": round(tempo_par, 4)
            })
            print(f" -> Concluído em {tempo_par:.4f}s")

    # -------------------------------------------------------------
    # 3. Consolidação dos dados (Exportação para CSV)
    # -------------------------------------------------------------
    campos = ["Versao", "Tamanho", "Processos", "Tempo_Segundos"]
    
    with open("resultados_benchmark.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(cenarios)
        
    print("\n=== BENCHMARK FINALIZADO ===")
    print("Dados extraídos com sucesso para 'resultados_benchmark.csv'.")
    print("Pronto para plotagem dos gráficos de Speedup e Eficiência!")

if __name__ == "__main__":
    rodar_benchmark()