import pandas as pd
import matplotlib.pyplot as plt

def gerar_graficos():
    # Lê os dados do benchmark
    try:
        df = pd.read_csv("resultados_benchmark.csv")
    except FileNotFoundError:
        print("Erro: Rode o benchmark.py primeiro para gerar os dados!")
        return

    # Exemplo: Filtra um cenário específico para plotar (Matriz 1000x1000, 50 gerações, 5%)
    cenario = df[(df['Matriz'] == '1000x1000') & (df['Geracoes'] == 50) & (df['Espalhadores'] == 0.05)]
    
    seq = cenario[cenario['Versao'] == 'Sequencial']
    par = cenario[cenario['Versao'] == 'Paralela']
    
    if seq.empty or par.empty:
        print("Dados insuficientes para gerar gráficos.")
        return

    tempo_seq = seq['Tempo_Segundos'].values[0]

    # Calcula Speedup e Eficiência
    par = par.copy() # Evita warning do pandas
    par['Speedup'] = tempo_seq / par['Tempo_Segundos']
    par['Eficiencia'] = par['Speedup'] / par['Processos']

    # --- Plotagem Speedup ---
    plt.figure(figsize=(8, 5))
    plt.plot(par['Processos'], par['Speedup'], marker='o', color='b', label='Paralelo')
    plt.plot(par['Processos'], par['Processos'], linestyle='--', color='r', label='Ideal (Linear)')
    plt.title("Curva de Speedup (Lei de Amdahl)")
    plt.xlabel("Número de Processos")
    plt.ylabel("Speedup (S)")
    plt.legend()
    plt.grid(True)
    plt.savefig("grafico_speedup.png")
    print("Gráfico de Speedup salvo!")

    # --- Plotagem Eficiência ---
    plt.figure(figsize=(8, 5))
    plt.plot(par['Processos'], par['Eficiencia'], marker='s', color='g')
    plt.axhline(y=1.0, linestyle='--', color='r', label='100% Eficiência')
    plt.title("Eficiência do Sistema")
    plt.xlabel("Número de Processos")
    plt.ylabel("Eficiência (E)")
    plt.ylim(0, 1.2)
    plt.legend()
    plt.grid(True)
    plt.savefig("grafico_eficiencia.png")
    print("Gráfico de Eficiência salvo!")

if __name__ == "__main__":
    gerar_graficos()