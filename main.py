# -*- coding: utf-8 -*-

import cv2
import pandas as pd
import os
import time

# =====================================================================================
# 1. CONFIGURAÇÃO GLOBAL DA APLICAÇÃO
# =====================================================================================
VIDEO_PATH = "C:/Users/zanat/Downloads/IMG_1592.MP4"
OUTPUT_CSV_PATH = VIDEO_PATH.split("/")[-1].replace(".MP4", "_analisado.csv")

CONFIG = {
    # --- JANELA E VÍDEO ---
    "WINDOW_NAME": "Analisador de Golpes - Tênis",
    # Código para virar o vídeo: 0=vertical, 1=horizontal, -1=ambos, None=não virar.
    "FLIP_VIDEO_CODE": -1,
    # --- OTIMIZAÇÃO DE DESEMPENHO ---
    # Reduz a resolução para a análise. 50 = 50% do tamanho original.
    # Use 100 para desativar. Valores entre 30 e 50 são recomendados para vídeos em HD/FullHD.
    "ANALYSIS_SCALE_PERCENT": 75,
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
        self.window_name = config["WINDOW_NAME"]

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
        self.point_counter = 0

        self._setup_ui()

    def _setup_ui(self):
        """Configura a janela da aplicação."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def _draw_overlay(self, frame):
        """Desenha o painel de ajuda e status na tela (versão otimizada)."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_pos = 40

        def draw_text(text, pos, color=(255, 255, 255), scale=0.7):
            cv2.putText(frame, text, pos, font, scale, color, 1, cv2.LINE_AA)

        # Painel de Status
        status_text = f"ESTADO: {'GRAVANDO PONTO' if self.current_state == 'RECORDING_POINT' else 'AGUARDANDO PONTO'}"
        status_color = (
            (0, 0, 255) if self.current_state == "RECORDING_POINT" else (0, 255, 255)
        )
        if self.is_paused:
            status_text += " (PAUSADO)"
        draw_text(status_text, (20, y_pos), status_color, scale=1.0)
        y_pos += 40

        # Último Evento Registrado
        if self.last_event_info:
            draw_text(f"Ultimo: {self.last_event_info}", (20, y_pos), (0, 255, 0))
            y_pos += 40

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
            "events": [],
        }
        self.current_state = "RECORDING_POINT"
        self.last_event_info = f"Ponto {self.point_counter} iniciado. Sacador: Jogador {event_info['code']}"
        print(
            f"\n--- Ponto {self.point_counter} iniciado (Sacador: {event_info['desc']}) em {timestamp:.2f}s ---"
        )

    def add_event_to_point(self, event_info):
        """Adiciona um evento (golpe) a um ponto em andamento."""
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Inicie um ponto primeiro (A ou B)!"
            return

        frame, timestamp = self._get_current_timestamp()
        self.current_point_data["events"].append(
            {
                "timestamp_sec": timestamp,
                "frame": frame,
                "event_code": event_info["code"],
                "event_desc": event_info["desc"],
            }
        )
        self.last_event_info = f"Golpe: {event_info['desc']}"
        print(f"  > Evento '{event_info['desc']}' adicionado em {timestamp:.2f}s")

    def end_point(self, event_info):
        """Finaliza o ponto atual e armazena os dados."""
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Nenhum ponto ativo para finalizar!"
            return

        self.add_event_to_point(event_info)
        frame, timestamp = self._get_current_timestamp()
        self.current_point_data["end_time_sec"] = timestamp
        self.current_point_data["duration_sec"] = (
            timestamp - self.current_point_data["start_time_sec"]
        )
        self.all_points_data.append(self.current_point_data)
        self.last_event_info = (
            f"Ponto {self.point_counter} finalizado: {event_info['desc']}"
        )
        print(
            f"--- Ponto {self.point_counter} finalizado. Duração: {self.current_point_data['duration_sec']:.2f}s ---\n"
        )
        self.current_state = "IDLE"
        self.current_point_data = None

    def delete_last_point(self):
        """
        Apaga o último ponto concluído ou cancela o ponto atualmente em gravação.
        """
        # Cenário 1: Cancela um ponto que está sendo gravado no momento.
        if self.current_state == "RECORDING_POINT":
            point_num_to_cancel = self.current_point_data["point_id"]
            self.current_state = "IDLE"
            self.current_point_data = None
            # Não decrementamos o point_counter para que o próximo ponto pegue este número.
            # Se preferir que o contador volte, descomente a linha abaixo.
            # self.point_counter -= 1

            self.last_event_info = (
                f"Ponto {point_num_to_cancel} em andamento foi cancelado."
            )
            print(f"\n--- Ponto {point_num_to_cancel} em andamento foi CANCELADO. ---")
            return

        # Cenário 2: Apaga o último ponto que foi concluído e salvo.
        if self.all_points_data:
            deleted_point = self.all_points_data.pop()
            self.point_counter -= 1  # Decrementa o contador geral de pontos

            point_id = deleted_point["point_id"]
            self.last_event_info = f"Ponto {point_id} foi APAGADO."
            print(f"\n--- Último ponto concluído (Ponto {point_id}) foi APAGADO. ---")
        else:
            # Cenário 3: Não há nada para apagar.
            self.last_event_info = "Nenhum ponto para apagar."
            print("\n--- Nenhum ponto concluído para apagar. ---")

    def save_to_csv(self):
        """Converte os dados coletados para um DataFrame e salva como CSV."""
        if not self.all_points_data:
            print("Nenhum ponto foi gravado. Nenhum arquivo CSV será gerado.")
            return

        output_data = []
        for point in self.all_points_data:
            for event in point["events"]:
                output_data.append(
                    {
                        "point_id": point["point_id"],
                        "server": point["server"],
                        "point_start_time_sec": point["start_time_sec"],
                        "point_end_time_sec": point.get("end_time_sec"),
                        "point_duration_sec": point.get("duration_sec"),
                        "event_timestamp_sec": event["timestamp_sec"],
                        "event_frame": event["frame"],
                        "event_code": event["event_code"],
                        "event_description": event["event_desc"],
                    }
                )

        df = pd.DataFrame(output_data)
        df.to_csv(OUTPUT_CSV_PATH, index=False, sep=";", decimal=",")
        print(f"\nAnálise salva com sucesso em: {self.config['OUTPUT_CSV_PATH']}")

    def run(self):
        """Inicia o loop principal com lógica de reprodução corrigida e otimizada."""
        current_frame_num = 0
        scale_percent = self.config.get("ANALYSIS_SCALE_PERCENT", 100)

        while self.cap.isOpened():
            # Define a posição do vídeo, garantindo que não ultrapasse os limites
            current_frame_num = max(0, min(current_frame_num, self.total_frames - 1))
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

            self._draw_overlay(frame)
            cv2.imshow(self.window_name, frame)

            key = cv2.waitKey(1)

            # Lógica de Controle
            if key == ord("x"):
                break
            elif key == ord(" "):
                self.is_paused = not self.is_paused
            elif key == ord("z"):
                self.delete_last_point()
                self.is_paused = True  # Pausa para o usuário ver o feedback

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
                    self.add_event_to_point(event_info)
                elif action == "END_POINT":
                    self.end_point(event_info)

            # Avança para o próximo quadro somente se não estiver pausado
            if not self.is_paused:
                current_frame_num += 5

            if current_frame_num >= self.total_frames - 1:
                self.is_paused = True

        self.cap.release()
        cv2.destroyAllWindows()
        self.save_to_csv()


if __name__ == "__main__":
    # Verifica se as dependências estão instaladas
    try:
        import cv2
        import pandas as pd
    except ImportError:
        print("ERRO: Dependências não encontradas.")
        print("Por favor, instale-as com o comando: pip install opencv-python pandas")
        exit()

    try:
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

    except Exception as e:
        print(f"Ocorreu um erro fatal: {e}")
