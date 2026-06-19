import pandas as pd
import matplotlib.pyplot as plt

def gerar_graficos():
    # 1. Lê os dados do benchmark
    try:
        df = pd.read_csv("resultados_benchmark.csv")
    except FileNotFoundError:
        print("Erro: Rode o benchmark.py primeiro para gerar os dados!")
        return

    print("Gerando gráficos oficiais para a apresentação...")

    # =========================================================================
    # GRÁFICO 1: Tempo x Tamanho de Matriz (Comparação das 3 versões)
    # =========================================================================
    df_g1 = df[(df['Geracoes'] == 50) & (df['Espalhadores'] == 0.05)]
    
    seq_g1 = df_g1[df_g1['Versao'] == 'Sequencial']
    par_g1 = df_g1[(df_g1['Versao'] == 'Paralela') & (df_g1['Processos'] == 4)] # Usa 4 processos para base
    dist_g1 = df_g1[(df_g1['Versao'] == 'Distribuida') & (df_g1['Processos'] == 4)] # Usa 4 clientes para base

    plt.figure(figsize=(10, 6))
    if not seq_g1.empty:
        plt.plot(seq_g1['Matriz'], seq_g1['Tempo_Segundos'], marker='o', label='Sequencial', color='black', linestyle='--')
    if not par_g1.empty:
        plt.plot(par_g1['Matriz'], par_g1['Tempo_Segundos'], marker='s', label='Paralela (4 Proc)', color='blue')
    if not dist_g1.empty:
        plt.plot(dist_g1['Matriz'], dist_g1['Tempo_Segundos'], marker='^', label='Distribuída (4 Clientes)', color='orange')
    
    plt.title("Tempo de Execução vs Tamanho da Matriz")
    plt.xlabel("Tamanho da Matriz")
    plt.ylabel("Tempo (Segundos)")
    plt.legend()
    plt.grid(True)
    plt.savefig("grafico_1_tempo_vs_tamanho.png")
    print(" -> Gráfico 1 (Tempo x Tamanho) salvo!")

    # =========================================================================
    # CONFIGURAÇÃO BASE PARA SPEEDUP E EFICIÊNCIA
    # =========================================================================
    cenario_pesado = df[(df['Matriz'] == '1000x1000') & (df['Geracoes'] == 50) & (df['Espalhadores'] == 0.05)]
    seq_pesado = cenario_pesado[cenario_pesado['Versao'] == 'Sequencial']
    
    if seq_pesado.empty:
        print("Faltam dados da versão Sequencial para gerar Speedup e Eficiência.")
        return
        
    tempo_seq = seq_pesado['Tempo_Segundos'].values[0]

    par_pesado = cenario_pesado[cenario_pesado['Versao'] == 'Paralela'].copy()
    dist_pesado = cenario_pesado[cenario_pesado['Versao'] == 'Distribuida'].copy()

    # =========================================================================
    # GRÁFICO 2: Curvas de Speedup (Lei de Amdahl)
    # =========================================================================
    plt.figure(figsize=(10, 6))
    
    if not par_pesado.empty:
        par_pesado['Speedup'] = tempo_seq / par_pesado['Tempo_Segundos']
        plt.plot(par_pesado['Processos'], par_pesado['Speedup'], marker='s', color='blue', label='Paralela')
        
    if not dist_pesado.empty:
        dist_pesado['Speedup'] = tempo_seq / dist_pesado['Tempo_Segundos']
        plt.plot(dist_pesado['Processos'], dist_pesado['Speedup'], marker='^', color='orange', label='Distribuída')

    # Cria a linha ideal baseada no número máximo de processos testados
    max_proc = max(par_pesado['Processos'].max() if not par_pesado.empty else 0, 
                   dist_pesado['Processos'].max() if not dist_pesado.empty else 0)
    
    if max_proc > 0:
        plt.plot([1, max_proc], [1, max_proc], linestyle='--', color='red', label='Ideal (Linear)')

    plt.title("Curva de Speedup (Lei de Amdahl) - Matriz 1000x1000")
    plt.xlabel("Número de Processos / Clientes")
    plt.ylabel("Speedup (S)")
    plt.legend()
    plt.grid(True)
    plt.savefig("grafico_2_speedup.png")
    print(" -> Gráfico 2 (Speedup) salvo!")

    # =========================================================================
    # GRÁFICO 3: Eficiência do Sistema
    # =========================================================================
    plt.figure(figsize=(10, 6))
    
    if not par_pesado.empty:
        par_pesado['Eficiencia'] = par_pesado['Speedup'] / par_pesado['Processos']
        plt.plot(par_pesado['Processos'], par_pesado['Eficiencia'], marker='s', color='green', label='Paralela')
        
    if not dist_pesado.empty:
        dist_pesado['Eficiencia'] = dist_pesado['Speedup'] / dist_pesado['Processos']
        plt.plot(dist_pesado['Processos'], dist_pesado['Eficiencia'], marker='d', color='purple', label='Distribuída')

    plt.axhline(y=1.0, linestyle='--', color='red', label='100% Eficiência')
    plt.title("Eficiência do Sistema - Matriz 1000x1000")
    plt.xlabel("Número de Processos / Clientes")
    plt.ylabel("Eficiência (E)")
    plt.ylim(0, 1.2)
    plt.legend()
    plt.grid(True)
    plt.savefig("grafico_3_eficiencia.png")
    print(" -> Gráfico 3 (Eficiência) salvo!")

    # =========================================================================
    # GRÁFICO 4: Análise de Gargalo de Comunicação (Distribuída vs Sequencial)
    # =========================================================================
    plt.figure(figsize=(10, 6))
    dist_all = df[df['Versao'] == 'Distribuida']
    
    if not dist_all.empty:
        # Pega cenários específicos para a distribuída
        for clientes in sorted(dist_all['Processos'].unique()):
            dados_cli = dist_all[(dist_all['Processos'] == clientes) & (dist_all['Geracoes'] == 50) & (dist_all['Espalhadores'] == 0.05)]
            plt.plot(dados_cli['Matriz'], dados_cli['Tempo_Segundos'], marker='^', label=f'Distribuída ({clientes} Clientes)')
        
        # Plota o Sequencial como linha de base negra pontilhada
        plt.plot(seq_g1['Matriz'], seq_g1['Tempo_Segundos'], marker='o', color='black', linestyle='--', label='Sequencial (Baseline)')
            
        plt.title("Análise de Gargalo de Rede: Tempo vs Clientes")
        plt.xlabel("Tamanho da Matriz")
        plt.ylabel("Tempo (Segundos)")
        plt.legend()
        plt.grid(True)
        plt.savefig("grafico_4_gargalo_rede.png")
        print(" -> Gráfico 4 (Gargalo de Rede) salvo!")

if __name__ == "__main__":
    gerar_graficos()