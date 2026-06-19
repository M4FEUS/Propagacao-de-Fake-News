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
    # Cenários de carga de trabalho 
    tamanhos_matriz = [100, 500, 1000]
    cenarios_geracoes = [10, 50, 100]
    cenarios_espalhadores = [0.02, 0.05, 0.10] # 2%, 5%, 10%
    num_processos = [1, 2, 4, 8]
    
    resultados = []

    print("=== INICIANDO PIPELINE DE BENCHMARK COMPLETO ===")

    for tam in tamanhos_matriz:
        for gen in cenarios_geracoes:
            for esp in cenarios_espalhadores:
                
                print(f"\n--- Cenário: {tam}x{tam} | {gen} Ger | {esp*100}% Espalhadores ---")
                
                # 1. SEQUENCIAL (Baseline)
                cmd_seq = [
                    "python", "fakenews_sequencial.py",
                    "--linhas", str(tam), "--colunas", str(tam),
                    "--geracoes", str(gen), "--espalhadores", str(esp),
                    "--multiplas-noticias"
                ]
                print("Rodando Sequencial...")
                inicio = time.time()
                res_seq = subprocess.run(cmd_seq, capture_output=True, text=True)
                t_seq = extrair_tempo(res_seq.stdout) or (time.time() - inicio)
                resultados.append({"Versao": "Sequencial", "Matriz": f"{tam}x{tam}", "Geracoes": gen, "Espalhadores": esp, "Processos": 1, "Tempo_Segundos": round(t_seq, 4)})

                # 2. PARALELA 
                for p in num_processos:
                    cmd_par = [
                        "python", "fakenews_paralelo.py",
                        "--linhas", str(tam), "--colunas", str(tam),
                        "--geracoes", str(gen), "--espalhadores", str(esp),
                        "--multiplas-noticias", "--processos", str(p)
                    ]
                    print(f"Rodando Paralela ({p} processos)...")
                    inicio = time.time()
                    res_par = subprocess.run(cmd_par, capture_output=True, text=True)
                    if res_par.returncode == 0:
                        t_par = extrair_tempo(res_par.stdout) or (time.time() - inicio)
                        resultados.append({"Versao": "Paralela", "Matriz": f"{tam}x{tam}", "Geracoes": gen, "Espalhadores": esp, "Processos": p, "Tempo_Segundos": round(t_par, 4)})
                    else:
                        print(" -> Ignorado (Arquivo M2 não encontrado ou falhou)")

                # 3. DISTRIBUÍDA
                for p in [2, 4]: # O roteiro pede processos: 2, 4 para distribuído
                    cmd_dist = [
                        "python", "servidor.py",
                        "--linhas", str(tam), "--colunas", str(tam),
                        "--geracoes", str(gen), "--espalhadores", str(esp),
                        "--multiplas-noticias", "--clientes", str(p),
                        "--auto" 
                    ]
                    print(f"Rodando Distribuída ({p} clientes)...")
                    inicio = time.time()
                    res_dist = subprocess.run(cmd_dist, capture_output=True, text=True)
                    if res_dist.returncode == 0:
                        t_dist = extrair_tempo(res_dist.stdout) or (time.time() - inicio)
                        resultados.append({"Versao": "Distribuida", "Matriz": f"{tam}x{tam}", "Geracoes": gen, "Espalhadores": esp, "Processos": p, "Tempo_Segundos": round(t_dist, 4)})
                    else:
                        print(" -> Ignorado (Arquivo M3 não encontrado ou falhou)")

    # Consolidação CSV
    campos = ["Versao", "Matriz", "Geracoes", "Espalhadores", "Processos", "Tempo_Segundos"]
    with open("resultados_benchmark.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)
        
    print("\n=== BENCHMARK FINALIZADO COM SUCESSO ===")

if __name__ == "__main__":
    rodar_benchmark()