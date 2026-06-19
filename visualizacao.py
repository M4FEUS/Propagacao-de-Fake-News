import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import ListedColormap
from copy import deepcopy
from fakenews_sequencial import (
    criar_grade, criar_grade_vazia, proxima_geracao, total_espalhadores_ativos, contar_estados
)

def gerar_animacao(linhas=50, colunas=50, geracoes=50):
    # Inicializa as grades
    grade_a = criar_grade(linhas, colunas, percentual_espalhadores=0.05, semente=42, multiplas_noticias=True)
    grade_b = criar_grade_vazia(linhas, colunas)
    
    # Armazena o histórico para o frame da animação
    historico = [deepcopy(grade_a)]
    
    for _ in range(geracoes):
        proxima_geracao(grade_a, grade_b, limiar_convencimento=2, multiplas_noticias=True, matriz_credulidade=None)
        grade_a, grade_b = grade_b, grade_a
        historico.append(deepcopy(grade_a))
        
        if total_espalhadores_ativos(contar_estados(grade_a)) == 0:
            break

    # Configuração de Cores: 0=Azul, 1=Vermelho, 2=Cinza, 3=Laranja, 4=Verde (Agência)
    cmap = ListedColormap(['#3498db', '#e74c3c', '#95a5a6', '#e67e22', '#2ecc71'])
    
    # Cria a figura e os eixos PRIMEIRO
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title("Propagação de Fake News - Geração 0")
    
    # Plota a matriz usando vmax=4 (para incluir o estado da Agência)
    matriz_plot = ax.matshow(historico[0], cmap=cmap, vmin=0, vmax=4)
    ax.axis('off')

    def atualizar(frame):
        matriz_plot.set_data(historico[frame])
        ax.set_title(f"Propagação de Fake News - Geração {frame}")
        return [matriz_plot]

    anim = animation.FuncAnimation(fig, atualizar, frames=len(historico), interval=200, blit=False)
    
    # Para salvar em vídeo, descomente a linha abaixo (requer ffmpeg instalado):
    # anim.save('simulacao_fakenews.mp4', fps=5, extra_args=['-vcodec', 'libx264'])
    
    plt.show()

if __name__ == "__main__":
    gerar_animacao()