import cv2
import pandas as pd
import os
import time

# =====================================================================================
# 1. CONFIGURAÇÃO GLOBAL DA APLICAÇÃO
# =====================================================================================
VIDEO_PATH = "C:/Users/adriez01/Downloads/IMG_4076.MP4"
OUTPUT_CSV_PATH_POINTS = VIDEO_PATH.split("/")[-1].replace(".MP4", "_POINTS.csv")
OUTPUT_CSV_PATH_EVENTS = VIDEO_PATH.split("/")[-1].replace(".MP4", "_EVENTS.csv")
CONFIG = {
    # Código para virar o vídeo: 0=vertical, 1=horizontal, -1=ambos, None=não virar.
    "FLIP_VIDEO_CODE": None,
    # --- OTIMIZAÇÃO DE DESEMPENHO ---
    # Reduz a resolução para a análise. 50 = 50% do tamanho original.
    # Use 100 para desativar. Valores entre 30 e 50 são recomendados para vídeos em HD/FullHD.
    "ANALYSIS_SCALE_PERCENT": 50,
    # --- TABELA DE CÓDIGOS E MAPEAMENTO DE TECLAS ---
    "KEY_MAPPINGS": {
        # --- CLASSE: Jogador (Inicia um ponto) ---
        ord("A"): {"action": "START_POINT", "code": "A", "desc": "Jogador A"},
        ord("B"): {"action": "START_POINT", "code": "B", "desc": "Jogador B"},
        # --- CLASSE: Golpe (Adiciona um evento durante o ponto) ---
        ord("1"): {"action": "ADD_EVENT", "code": "1", "desc": "1st Serve"},
        ord("2"): {"action": "ADD_EVENT", "code": "2", "desc": "2nd Serve"},
        ord("f"): {"action": "ADD_EVENT", "code": "F", "desc": "Forehand"},
        ord("b"): {"action": "ADD_EVENT", "code": "B", "desc": "Backhand"},
        ord("d"): {"action": "ADD_EVENT", "code": "D", "desc": "Dropshot"},
        ord("m"): {"action": "ADD_EVENT", "code": "M", "desc": "Smash"},
        ord("v"): {"action": "ADD_EVENT", "code": "V", "desc": "Volley"},
        ord("s"): {"action": "ADD_EVENT", "code": "S", "desc": "Slice"},
        # --- CLASSE: Resultado Golpe (Finaliza o ponto) ---
        ord("e"): {"action": "END_POINT", "code": "E", "desc": "Error"},
        ord("w"): {"action": "END_POINT", "code": "W", "desc": "Winner"},
    },
}


class TennisVideoAnalyzer:
    """
    Classe completa para analisar vídeos de tênis, capturando eventos
    de cada ponto e salvando os resultados em um arquivo CSV.
    """

    def __init__(self, config):
        self.config = config
        self.video_path = VIDEO_PATH
        self.window_name = "Analisador de Golpes - Tênis"

        if not os.path.exists(self.video_path):
            raise FileNotFoundError(
                f"Arquivo de vídeo não encontrado em: {self.video_path}"
            )

        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.is_paused = True  # Começa pausado para o usuário se preparar
        self.current_state = "IDLE"
        self.last_event_info = "Pressione ESPAÇO para iniciar."

        self.all_points_data = []
        self.current_point_data = None
        self.all_events_data = []
        self.current_event_data = None
        self.point_counter = 0
        self.score = {"A": 0, "B": 0}

        self._setup_ui()

    def _setup_ui(self):
        """Configura a janela da aplicação."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def _get_current_timestamp(self):
        """Retorna o número e o timestamp em segundos do quadro atual."""
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        timestamp_sec = current_frame / self.fps if self.fps > 0 else 0
        return current_frame, timestamp_sec

    def start_new_point(self, event_info):
        """Inicia a gravação de um novo ponto."""
        if self.current_state == "RECORDING_POINT":
            self.last_event_info = "ERRO: Ponto atual precisa ser finalizado!"
            print(
                f"\nAVISO: Ponto {self.point_counter} está ativo. Finalize-o com 'e' ou 'w'."
            )
            return

        self.point_counter += 1
        frame, timestamp = self._get_current_timestamp()

        self.current_point_data = {
            "point_id": self.point_counter,
            "server": event_info["code"],
            "start_time_sec": timestamp,
        }
        self.current_state = "RECORDING_POINT"
        self.last_event_info = f"Ponto {self.point_counter} iniciado. Sacador: Jogador {event_info['code']}"
        print(
            f"\n--- Ponto {self.point_counter} iniciado (Sacador: {event_info['desc']}) em {timestamp:.2f}s ---"
        )

    def add_event(self, event_info):
        """Adiciona um evento (golpe) a um ponto em andamento."""
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Inicie um ponto primeiro (A ou B)!"
            return

        frame, timestamp = self._get_current_timestamp()
        self.current_event_data = {
            "point_id": self.point_counter,
            "timestamp_sec": timestamp,
            "frame": frame,
            "event_code": event_info["code"],
        }
        self.all_events_data.append(self.current_event_data)
        self.last_event_info = f"Golpe: {event_info['desc']}"
        print(f"  > Golpe '{event_info['desc']}' adicionado em {timestamp:.2f}s")

    def end_point(self, event_info):
        """Finaliza o ponto atual e armazena os dados."""
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Nenhum ponto ativo para finalizar!"
            return

        frame, timestamp = self._get_current_timestamp()
        self.current_point_data["end_time_sec"] = timestamp
        self.all_points_data.append(self.current_point_data)

        self.last_event_info = (
            f"Ponto {self.point_counter} finalizado: {event_info['desc']}"
        )
        print(f"--- Ponto {self.point_counter} finalizado. ---\n")
        self.current_state = "IDLE"
        self.current_point_data = None

    def delete_point_event(self):
        if self.current_state == "RECORDING_POINT":
            point_to_delete = self.point_counter
            self.current_point_data = None
            self.point_counter -= 1
            self.all_events_data = [
                event
                for event in self.all_events_data
                if event["point_id"] != point_to_delete
            ]
            print(f"\nPonto {point_to_delete} deletado com sucesso.\n")
        elif self.current_state == "IDLE":
            if self.all_points_data:
                point_to_delete = self.point_counter - 1
                self.all_points_data.pop()
                self.all_events_data = [
                    event
                    for event in self.all_events_data
                    if event["point_id"] != point_to_delete
                ]
                print("\nÚltimo ponto deletado com sucesso.\n")
        else:
            print("\nNenhum ponto para deletar.\n")

    def save_to_csv(self):
        """Converte os dados coletados para um DataFrame e salva como CSV."""
        if not self.all_points_data:
            print("Nenhum ponto foi gravado. Nenhum arquivo CSV será gerado.")
            return

        df_points = pd.DataFrame(self.all_points_data)
        df_points.to_csv(OUTPUT_CSV_PATH_POINTS, index=False, sep=";", decimal=",")

        df_events = pd.DataFrame(self.all_events_data)
        df_events.to_csv(OUTPUT_CSV_PATH_EVENTS, index=False, sep=";", decimal=",")

        print(f"\nAnálise salva com sucesso em: {OUTPUT_CSV_PATH_POINTS}")
        print(f"Eventos salvos em: {OUTPUT_CSV_PATH_EVENTS}")

    def run(self):
        """Inicia o loop principal com lógica de reprodução corrigida e otimizada."""
        current_frame_num = 0
        scale_percent = self.config.get("ANALYSIS_SCALE_PERCENT", 100)

        while self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_num)

            ret, frame = self.cap.read()
            if not ret:
                break

            # Otimização de Desempenho
            if scale_percent < 100:
                width = int(frame.shape[1] * scale_percent / 100)
                height = int(frame.shape[0] * scale_percent / 100)
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            if self.config["FLIP_VIDEO_CODE"] is not None:
                frame = cv2.flip(frame, self.config["FLIP_VIDEO_CODE"])

            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1)

            # Lógica de Controle
            if key == ord("x"):
                break
            elif key == ord(" "):
                self.is_paused = not self.is_paused
            elif key == ord("z"):
                self.delete_point_event()
                continue

            # Navegação por quadros
            elif key == ord("k"):
                current_frame_num += 1
            elif key == ord("K"):
                current_frame_num -= 1
            elif key == ord("l"):
                current_frame_num += 10
            elif key == ord("j"):
                current_frame_num -= 10
            elif key == ord("L"):
                current_frame_num += 150
            elif key == ord("J"):
                current_frame_num -= 150

            # Processamento de eventos de jogo
            elif key in self.config["KEY_MAPPINGS"]:
                self.is_paused = True  # Pausa ao registrar um evento para evitar erros
                event_info = self.config["KEY_MAPPINGS"][key]
                action = event_info["action"]

                if action == "START_POINT":
                    self.start_new_point(event_info)
                elif action == "ADD_EVENT":
                    self.add_event(event_info)
                elif action == "END_POINT":
                    self.add_event(event_info)
                    self.end_point(event_info)

            # Avança para o próximo quadro somente se não estiver pausado
            if not self.is_paused:
                current_frame_num += 3

            if current_frame_num >= self.total_frames - 1:
                self.is_paused = True

        self.cap.release()
        cv2.destroyAllWindows()
        self.save_to_csv()


if __name__ == "__main__":
    # Verifica se as dependências estão instaladas
    print("""Atalhos disponíveis:
            - 'A' para Jogador A iniciar ponto
            - 'B' para Jogador B iniciar ponto
            - '1', '2', 'f', 'b', 'd', 'm', 'v', 's' para adicionar eventos
            - 'e' para finalizar ponto com erro
            - 'w' para finalizar ponto com winner
            - 'z' para apagar o último ponto
            - 'x' para sair do programa
            - Use as teclas de navegação (k, K, l, j, L, J) para controlar os quadros""")
    analyzer = TennisVideoAnalyzer(CONFIG)
    analyzer.run()
