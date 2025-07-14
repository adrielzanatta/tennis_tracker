import sys
import os

# =====================================================================================
# 1. CONFIGURAÇÃO GLOBAL DA APLICAÇÃO
# =====================================================================================
if len(sys.argv) > 1:
    VIDEO_PATH = sys.argv[1]
else:
    raise ValueError(
        "Por favor, forneça o caminho do vídeo como argumento: python main.py <caminho_do_video>"
    )

# Geração mais robusta do caminho de saída do CSV
video_filename = os.path.basename(VIDEO_PATH)
video_name_without_ext = os.path.splitext(video_filename)[0]
OUTPUT_CSV_DIR = "../Analises/temp"
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)  # Garante que o diretório existe
OUTPUT_CSV_PATH = os.path.join(
    OUTPUT_CSV_DIR, f"{video_name_without_ext}_analisado.csv"
)
print(f"Arquivo de saída será: {OUTPUT_CSV_PATH}")

print(f"Caminho do vídeo: {VIDEO_PATH}")
print(f"Caminho do CSV: {OUTPUT_CSV_PATH}")

CONFIG = {
    # --- JANELA E VÍDEO ---
    "WINDOW_NAME": "Analisador de Golpes - Tênis (Otimizado)",
    "FLIP_VIDEO_CODE": None,  # Mude para 0 ou 1 se precisar virar o vídeo
    # --- OTIMIZAÇÃO DE DESEMPENHO ---
    # --- JOGADORES ---
    "PLAYER_A_NAME": "JOGADOR A",
    "PLAYER_B_NAME": "JOGADOR B",
    "ANALYSIS_SCALE_PERCENT": 100,  # Reduz para 30% para análise, muito mais rápido
    "THREAD_QUEUE_SIZE": 300,  # Frames para bufferizar em memória. 128 ou 256 é um bom valor.
    # --- CONTROLES ---
    "KEY_MAPPINGS": {
        # ... (seu mapeamento de teclas permanece o mesmo) ...
        ord("A"): {"action": "START_POINT", "code": "A", "desc": "Jogador A"},
        ord("B"): {"action": "START_POINT", "code": "B", "desc": "Jogador B"},
        ord("1"): {"action": "ADD_EVENT", "code": "1", "desc": "1st Serve"},
        ord("2"): {"action": "ADD_EVENT", "code": "2", "desc": "2nd Serve"},
        ord("f"): {"action": "ADD_EVENT", "code": "F", "desc": "Forehand"},
        ord("b"): {"action": "ADD_EVENT", "code": "B", "desc": "Backhand"},
        ord("d"): {"action": "ADD_EVENT", "code": "D", "desc": "Dropshot"},
        ord("m"): {"action": "ADD_EVENT", "code": "M", "desc": "Smash"},
        ord("v"): {"action": "ADD_EVENT", "code": "V", "desc": "Volley"},
        ord("s"): {"action": "ADD_EVENT", "code": "S", "desc": "Slice"},
        ord("e"): {"action": "END_POINT", "code": "E", "desc": "Error"},
        ord("w"): {"action": "END_POINT", "code": "W", "desc": "Winner"},
    },
}
