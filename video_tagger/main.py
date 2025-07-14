import cv2
import pandas as pd
import time
import copy
import os

# Importações dos módulos refatorados
from config import CONFIG, VIDEO_PATH, OUTPUT_CSV_PATH
from video_stream import VideoStream
from game import TennisGame
from scoreboard import Scoreboard


class TennisVideoAnalyzer:
    def __init__(self, config):
        self.config = config
        self.video_path = VIDEO_PATH
        self.window_name = config["WINDOW_NAME"]

        # Inicializa o VideoStream otimizado em vez do cv2.VideoCapture
        self.vs = VideoStream(self.video_path, config["THREAD_QUEUE_SIZE"])
        if not self.vs.stream.isOpened():
            raise FileNotFoundError(f"Erro ao abrir o vídeo: {self.video_path}")
        print(f"Vídeo carregado com sucesso: {self.video_path}")
        self.total_frames = self.vs.total_frames or 1
        self.fps = self.vs.fps
        time.sleep(5.0)  # Espera 2s para o buffer da thread encher um pouco

        self.is_paused = True
        self.current_state = "IDLE"
        self.last_event_info = "Pressione ESPAÇO para iniciar."
        self.current_frame_num = 0
        self.playback_speed = 1

        self.all_points_data = []
        self.current_point_data = None
        self.point_counter = 0

        # --- INICIALIZAÇÃO DO JOGO E DO APRESENTADOR DO PLACAR ---
        self.game = TennisGame(config["PLAYER_A_NAME"], config["PLAYER_B_NAME"])
        self.game_history = []  # Para poder desfazer o estado do jogo
        # Jogo que será efetivamente exibido, sincronizado com o frame atual
        self.display_game = TennisGame(config["PLAYER_A_NAME"], config["PLAYER_B_NAME"])
        self.scoreboard_presenter = Scoreboard()

        self.current_player = None

        self._setup_ui()

    def _setup_ui(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def _draw_overlay(self, frame):
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_pos = 30

        def draw_text(text, pos, color=(255, 255, 255), scale=0.7):
            cv2.putText(frame, text, pos, font, scale, color, 1, cv2.LINE_AA)

        status_text = f"ESTADO: {'GRAVANDO PONTO' if self.current_state == 'RECORDING_POINT' else 'AGUARDANDO'}"
        status_color = (
            (0, 255, 0) if self.current_state == "RECORDING_POINT" else (0, 255, 255)
        )

        playback_info = "(PAUSADO)" if self.is_paused else f"({self.playback_speed}x)"
        draw_text(
            f"{status_text} {playback_info}", (20, y_pos), status_color, scale=1.0
        )
        y_pos += 40

        if self.last_event_info:
            draw_text(f"Ultimo: {self.last_event_info}", (20, y_pos), (50, 205, 255))
            y_pos += 40

        frame_info = f"Frame: {self.current_frame_num}/{self.total_frames}"
        draw_text(frame_info, (20, y_pos), (255, 255, 255))

        # --- DESENHAR O PLACAR ---
        self._draw_wimbledon_scoreboard(frame)

    def _draw_wimbledon_scoreboard(self, frame):
        # Cores (BGR)
        WIMBLEDON_GREEN = (44, 88, 0)
        WHITE = (255, 255, 255)
        YELLOW = (0, 255, 255)
        FONT = cv2.FONT_HERSHEY_DUPLEX  # Fonte mais estilizada

        # Pega as dimensões do frame para posicionar o placar no canto inferior esquerdo
        frame_h, frame_w, _ = frame.shape
        board_h = 85
        board_w = 450
        start_x = 20
        start_y = frame_h - board_h - 20  # 20px de margem inferior

        # Desenha o retângulo de fundo com transparência
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (start_x, start_y),
            (start_x + board_w, start_y + board_h),
            WIMBLEDON_GREEN,
            -1,
        )
        alpha = 0.8
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        # Pega os dados do placar
        score_data = self.scoreboard_presenter.get_score_data(self.display_game)

        if score_data.get("match_over"):
            winner_text = f"VENCEDOR: {score_data['winner']}"
            (w, h), _ = cv2.getTextSize(winner_text, FONT, 0.8, 2)
            text_x = start_x + (board_w - w) // 2
            text_y = start_y + (board_h + h) // 2
            cv2.putText(
                frame, winner_text, (text_x, text_y), FONT, 0.8, YELLOW, 2, cv2.LINE_AA
            )
            return

        # Posições das colunas
        col_name = start_x + 25
        col_sets_start = col_name + 150
        col_games = col_sets_start + 100
        col_points = col_games + 60

        def draw_player_row(y_pos, player_data):
            cv2.putText(
                frame,
                player_data["name"],
                (col_name, y_pos),
                FONT,
                0.6,
                WHITE,
                1,
                cv2.LINE_AA,
            )
            set_x_offset = 0
            for s in player_data["sets_hist"]:
                cv2.putText(
                    frame,
                    str(s),
                    (col_sets_start + set_x_offset, y_pos),
                    FONT,
                    0.7,
                    WHITE,
                    2,
                    cv2.LINE_AA,
                )
                set_x_offset += 35
            cv2.putText(
                frame,
                str(player_data["games"]),
                (col_games, y_pos),
                FONT,
                0.7,
                WHITE,
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                player_data["points_str"],
                (col_points, y_pos),
                FONT,
                0.7,
                YELLOW,
                2,
                cv2.LINE_AA,
            )
            if player_data["is_server"]:
                cv2.circle(frame, (col_name - 15, y_pos - 5), 4, YELLOW, -1)

        draw_player_row(start_y + 35, score_data["pA"])
        draw_player_row(start_y + 70, score_data["pB"])

    def _get_current_timestamp(self):
        timestamp_sec = self.current_frame_num / self.fps if self.fps > 0 else 0
        return self.current_frame_num, timestamp_sec

    def start_new_point(self, event_info):
        if self.current_state == "RECORDING_POINT":
            self.last_event_info = "ERRO: Ponto atual precisa ser finalizado!"
            return

        self.point_counter += 1
        frame, timestamp = self._get_current_timestamp()

        self.current_player = event_info["code"]
        self.current_point_data = {
            "point_id": self.point_counter,
            "server": self.current_player,
            "events": [],
        }

        self.current_state = "RECORDING_POINT"

        self.last_event_info = (
            f"Ponto {self.point_counter} iniciado. Sacador: {event_info['desc']}"
        )
        print(
            f"--- Ponto {self.point_counter} iniciado (Sacador: {event_info['desc']}) em {timestamp:.2f}s ---"
        )

    def add_event_to_point(self, event_info):
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Inicie um ponto primeiro (A ou B)!"
            return

        frame, timestamp = self._get_current_timestamp()
        self.current_point_data["events"].append(
            {
                "event_code": event_info["code"],
                "timestamp_sec": timestamp,
                "frame": frame,
            }
        )
        self.last_event_info = f"Golpe: {event_info['desc']}"
        print(f"  > Evento '{event_info['desc']}' adicionado em {timestamp:.2f}s")
        # Alterna o jogador para o próximo golpe
        self.current_player = "B" if self.current_player == "A" else "A"

    def point_winnner(self, point_data):
        # --- LÓGICA PARA DETERMINAR O VENCEDOR (conforme solicitado) ---
        server = point_data["events"][0]["event_code"]
        receiver = "B" if server == "A" else "A"
        num_shots = len(point_data["events"])
        last_shot_by_server = num_shots % 2 == 1
        last_event_code = point_data["events"][-1]["event_code"]

        if last_event_code == "W":  # Winner
            point_winner = server if last_shot_by_server else receiver
        else:  # Error ("E")
            point_winner = receiver if last_shot_by_server else server

        return point_winner

    def end_point(self, event_info):
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Nenhum ponto ativo para finalizar!"
            return

        point_winner = self.point_winnner(self.current_point_data)

        # Atualiza o estado do jogo com o vencedor do ponto.
        self.game.point_won_by(point_winner)

        # Salva o NOVO estado do jogo no histórico, associado ao frame final do ponto.
        frame_of_point_end = self.current_frame_num
        self.game_history.append((frame_of_point_end, copy.deepcopy(self.game)))

        self.all_points_data.append(self.current_point_data)
        self.last_event_info = (
            f"Ponto {self.point_counter} finalizado: {event_info['desc']}"
        )
        print(f"--- Ponto {self.point_counter} finalizado. ---")
        self.current_state = "IDLE"
        self.current_player = None
        self.current_point_data = None

    def delete_last_point(self):
        """Apaga o último ponto registrado, incluindo os carregados do CSV."""
        if self.current_state == "RECORDING_POINT":
            point_num_to_cancel = self.current_point_data["point_id"]
            self.current_state = "IDLE"
            self.current_point_data = None
            self.current_player = None
            self.point_counter -= 1
            self.last_event_info = (
                f"Ponto {point_num_to_cancel} em andamento foi cancelado."
            )
            print(f"--- Ponto {point_num_to_cancel} em andamento foi CANCELADO. ---")
            return

        if self.all_points_data:
            deleted_point = self.all_points_data.pop()
            self.point_counter -= 1
            if self.game_history:
                self.game_history.pop()

            # Recalcula o estado do jogo com base nos pontos restantes
            self.game.reset_match()
            self.game_history = []
            for point in self.all_points_data:
                point_winner = self.point_winnner(point)  # Usa o ponto da lista
                self.game.point_won_by(point_winner)
                frame_of_point_end = point["events"][-1]["frame"]
                self.game_history.append((frame_of_point_end, copy.deepcopy(self.game)))

            self.last_event_info = f"Ponto {deleted_point['point_id']} foi APAGADO."
            print(
                f"--- Último ponto concluído (Ponto {deleted_point['point_id']}) foi APAGADO. ---"
            )
        else:
            self.last_event_info = "Nenhum ponto para apagar."
            print("--- Nenhum ponto concluído para apagar. ---")

    def _update_game_for_frame(self):
        for frame, game_state in reversed(self.game_history):
            if self.current_frame_num >= frame:
                self.display_game = game_state
                return
        self.display_game.reset_match()

    def save_to_csv(self):
        """Salva os dados de análise no arquivo CSV, preservando os dados existentes."""
        if not self.all_points_data:
            print("Nenhum ponto foi gravado. Nenhum arquivo CSV será gerado.")
            return

        # Carrega os dados existentes do CSV, se houver
        if os.path.exists(OUTPUT_CSV_PATH):
            existing_df = pd.read_csv(OUTPUT_CSV_PATH, sep=";", decimal=",")
        else:
            existing_df = pd.DataFrame()

        # Converte os novos dados para DataFrame
        new_data = []
        for point in self.all_points_data:
            for event in point["events"]:
                new_data.append(
                    {
                        "point_id": point["point_id"],
                        "event_code": event["event_code"],
                        "event_frame": event["frame"],
                        "event_timestamp_sec": event["timestamp_sec"],
                    }
                )
        new_df = pd.DataFrame(new_data)

        # Combina os dados existentes com os novos
        combined_df = (
            pd.concat([existing_df, new_df]).drop_duplicates().reset_index(drop=True)
        )

        # Salva o DataFrame combinado no CSV
        combined_df.to_csv(OUTPUT_CSV_PATH, index=False, sep=";", decimal=",")
        print(f"Análise salva com sucesso em: {OUTPUT_CSV_PATH}")

    def load_from_csv(self):
        """Carrega eventos de um arquivo CSV e inicializa o estado do jogo."""
        if not os.path.exists(OUTPUT_CSV_PATH):
            print(f"Nenhum arquivo CSV encontrado em: {OUTPUT_CSV_PATH}")
            return

        df = pd.read_csv(OUTPUT_CSV_PATH, sep=";", decimal=",")
        if df.empty:
            print("O arquivo CSV está vazio. Nenhum dado para carregar.")
            return

        print(f"Carregando estado do CSV: {OUTPUT_CSV_PATH}")
        # Inicializa o estado do jogo e os pontos registrados
        self.all_points_data = []
        self.game.reset_match()
        self.game_history = []

        grouped_points = df.groupby("point_id")
        for point_id, events in grouped_points:
            point_data = {
                "point_id": point_id,
                "server": events.iloc[0]["event_code"],
                "events": [],
            }
            for _, event in events.iterrows():
                point_data["events"].append(
                    {
                        "event_code": event["event_code"],
                        "timestamp_sec": event["event_timestamp_sec"],
                        "frame": event["event_frame"],
                    }
                )
            self.all_points_data.append(point_data)

            # Atualiza o estado do jogo com base no último evento do ponto
            last_event = point_data["events"][-1]
            if last_event["event_code"] in ["W", "E"]:
                self.game.point_won_by(
                    point_data["server"]
                    if last_event["event_code"] == "W"
                    else ("B" if point_data["server"] == "A" else "A")
                )
                frame_of_point_end = point_data["events"][-1]["frame"]
                self.game_history.append((frame_of_point_end, copy.deepcopy(self.game)))

        # Define o frame atual para o último ponto registrado
        if self.all_points_data:
            last_frame = self.all_points_data[-1]["events"][-1]["frame"]
            if last_frame >= self.total_frames:
                print(
                    f"Frame {last_frame} fora do intervalo do vídeo. Ajustando para o final."
                )
                last_frame = self.total_frames - 1
            self.current_frame_num = last_frame
            self.point_counter = max([p["point_id"] for p in self.all_points_data])
            self.vs.seek(self.current_frame_num)
            print(f"Estado carregado. Iniciando do frame {self.current_frame_num}.")
            time.sleep(0.1)  # Aguarda 1 segundo para o buffer ser preenchido

    def stop_analyzer(self):
        self.vs.stop()
        cv2.destroyAllWindows()
        self.save_to_csv()

    def run(self):
        scale_percent = self.config.get("ANALYSIS_SCALE_PERCENT", 100)
        frame = None
        jump_target = -1

        # Carrega o estado do CSV antes de iniciar o loop principal
        print("Iniciando carregamento do estado do CSV...")
        self.load_from_csv()
        print("Carregamento do estado concluído. Iniciando reprodução...")

        while True:
            if not self.is_paused or frame is None:
                if self.vs.stopped and not self.vs.more():
                    print("Fim do vídeo ou buffer vazio.")
                    break

                for _ in range(self.playback_speed):
                    if self.vs.more():
                        frame = self.vs.read()
                        self.current_frame_num += 1
                    else:
                        print("Buffer vazio durante a reprodução.")
                        break

                # Atualiza o placar de exibição durante a reprodução normal
                self._update_game_for_frame()

            if frame is None:
                print("Nenhum frame disponível para exibição.")
                break

            display_frame = frame.copy()

            # Verifica se o frame foi carregado corretamente antes de acessar suas propriedades
            if frame is not None and scale_percent < 100:
                width = int(frame.shape[1] * scale_percent / 100)
                height = int(frame.shape[0] * scale_percent / 100)
                display_frame = cv2.resize(
                    frame, (width, height), interpolation=cv2.INTER_AREA
                )

            if self.config["FLIP_VIDEO_CODE"] is not None:
                display_frame = cv2.flip(display_frame, self.config["FLIP_VIDEO_CODE"])

            self._draw_overlay(display_frame)
            cv2.imshow(self.window_name, display_frame)

            wait_time = 1 if not self.is_paused else 0
            key = cv2.waitKey(wait_time) & 0xFF

            if key == ord("x"):
                print("Saindo do analisador.")
                break
            elif key == ord(" "):
                self.is_paused = not self.is_paused
                self.playback_speed = 1
            elif key == ord("z"):
                self.is_paused = True
                self.delete_last_point()
            elif key == ord("k"):
                jump_target = self.current_frame_num - 1
            elif key == ord("K"):
                jump_target = self.current_frame_num + 1
            elif key == ord("j"):
                jump_target = self.current_frame_num - 10
            elif key == ord("l"):
                jump_target = self.current_frame_num + 10
            elif key == ord("L"):
                jump_target = self.current_frame_num + int(self.fps * 3)
            elif key == ord("J"):
                jump_target = self.current_frame_num - int(self.fps * 3)

            if jump_target != -1:
                self.current_frame_num = max(0, min(jump_target, self.total_frames - 1))
                self.vs.seek(self.current_frame_num)
                frame = self.vs.read()
                self._update_game_for_frame()
                jump_target = -1

            if key in self.config["KEY_MAPPINGS"]:
                self.is_paused = True
                event_info = self.config["KEY_MAPPINGS"][key]
                action = event_info["action"]

                if action == "START_POINT":
                    self.start_new_point(event_info)

                self.add_event_to_point(event_info)

                if action == "END_POINT":
                    self.end_point(event_info)

        self.stop_analyzer()


if __name__ == "__main__":
    print("""
    ==================================================================
    Analisador de Tênis Otimizado - Comandos
    ==================================================================
    Controle de Playback:
      - ESPAÇO: Pausar / Continuar
      - p: Acelerar reprodução (1x, 2x, 4x, 8x...)
      - x: Sair e Salvar

    Navegação (apenas quando pausado):
      - j/k: Frame seguinte / anterior
      - J/K: Pular 1 segundo para frente / trás
      - l/L: Pular 5 segundos para frente / trás

    Marcação de Pontos:
      - A/B: Iniciar ponto (Sacador A ou B)
      - 1,2,f,b,d,m,v,s: Registrar golpes
      - e/w: Finalizar ponto (Erro / Winner)
      - z: Apagar último ponto / Cancelar ponto atual
    =================================================================
    """)
    analyzer = TennisVideoAnalyzer(CONFIG)
    analyzer.run()
