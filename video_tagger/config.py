CONFIG = {
    # --- JANELA E VÍDEO ---
    "WINDOW_NAME": "Analisador de Golpes - Tênis (Otimizado)",
    "FLIP_VIDEO_CODE": None,  # Mude para 0 ou 1 se precisar virar o vídeo
    
    # --- OTIMIZAÇÃO DE DESEMPENHO ---
    "ANALYSIS_SCALE_PERCENT": 60,  # Reduz para 60% para análise, mais rápido

    # --- JOGADORES ---
    "PLAYER_A_NAME": "JOGADOR A",
    "PLAYER_B_NAME": "JOGADOR B",
    
    # --- CONTROLES ---
    "KEY_MAPPINGS": {
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