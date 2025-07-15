import cv2
import time
import copy

import os
import subprocess
# Importações dos módulos refatorados
from config import CONFIG, VIDEO_PATH, OUTPUT_CSV_PATH
from video_stream import VideoStream
from game import TennisGame
from scoreboard import Scoreboard
from ui_handler import UIHandler
from csv_handler import CSVHandler


class TennisVideoAnalyzer:
    def __init__(self, config):
        self.config = config

        # --- LÓGICA DE TRANSCODIFICAÇÃO AUTOMÁTICA ---
        original_video_path = VIDEO_PATH
        video_dir = os.path.dirname(original_video_path)
        video_filename = os.path.basename(original_video_path)
        video_name, _ = os.path.splitext(video_filename)

        # Define o caminho para o vídeo otimizado
        optimized_video_path = os.path.join(video_dir, f"{video_name}_optimized_720p.mp4")
        self.video_path = original_video_path # Padrão

        if not os.path.exists(optimized_video_path):
            print(f"Versão otimizada não encontrada. Transcodificando '{original_video_path}'...")
            try:
                command = [
                    "ffmpeg", "-i", original_video_path,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "copy", "-vf", "scale=-1:720", # Preserva o aspect ratio
                    optimized_video_path
                ]
                # Roda o comando e suprime a saída normal, mas mostra erros
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                print(f"Vídeo transcodificado com sucesso para: {optimized_video_path}")
                self.video_path = optimized_video_path
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print("\nERRO: Falha ao transcodificar o vídeo com ffmpeg.")
                print("Certifique-se de que o ffmpeg está instalado e no PATH do sistema.")
                if isinstance(e, subprocess.CalledProcessError):
                    print(f"Detalhe do erro do FFmpeg:\n{e.stderr.decode()}")
                print("Continuando a análise com o vídeo original (pode ser lento).\n")
        else:
            print(f"Usando versão otimizada do vídeo: {optimized_video_path}")
            self.video_path = optimized_video_path

        self.window_name = config["WINDOW_NAME"]
        # --- INICIALIZAÇÃO DOS HANDLERS ---
        self.csv_handler = CSVHandler(OUTPUT_CSV_PATH)

        # Inicializa o VideoStream otimizado em vez do cv2.VideoCapture
        self.vs = VideoStream(self.video_path)  # PyAV will raise an error if it fails to open the video

        print(f"Vídeo carregado com sucesso: {self.video_path}")
        self.total_frames = self.vs.total_frames or 1
        self.fps = self.vs.fps

        self.is_paused = True
        self.current_state = "IDLE"
        self.last_event_info = "Pressione ESPAÇO para iniciar."
        self.current_frame_num = 0
        self.frame_increment = 1

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

        # O UIHandler agora é responsável por criar a janela
        self.ui_handler = UIHandler(self.window_name)

    def _get_current_timestamp(self):
        """Calculates the current timestamp in seconds based on the current frame number."""
        timestamp_sec = self.current_frame_num / self.fps if self.fps > 0 else 0
        return self.current_frame_num, timestamp_sec

    def start_new_point(self, event_info):
        if self.current_state == "RECORDING_POINT":
            self.last_event_info = "ERRO: Ponto atual precisa ser finalizado!"
            return

        self.point_counter += 1
        frame, timestamp = self._get_current_timestamp()

        self.current_player = event_info["code"]
        self.current_point_data = {  # Initialize current point data
            "point_id": self.point_counter,
            "events": [],
        }

        self.current_state = "RECORDING_POINT"

        self.last_event_info = (
            f"Ponto {self.point_counter} iniciado. Sacador: {event_info['desc']}"
        )
        print(
            f"--- Ponto {self.point_counter} iniciado (Sacador: {event_info['desc']}) em {timestamp:.2f}s ---"
        )
        # Adiciona o evento de início de ponto
        self.add_event_to_point(event_info)

    def add_event_to_point(self, event_info):
        """Adds a new event to the current point."""
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Inicie um ponto primeiro (A ou B)!"
            return

        frame, timestamp = self._get_current_timestamp()
        self.current_point_data["events"].append(
            {
                "event_code": event_info["code"],
                "event_timestamp_sec": timestamp,
                "event_frame": frame,
            }
        )
        self.last_event_info = f"Golpe: {event_info['desc']}"
        print(f"  > Evento '{event_info['desc']}' adicionado em {timestamp:.2f}s")
        # Alterna o jogador para o próximo golpe
        self.current_player = "B" if self.current_player == "A" else "A"

    def point_winnner(self, point_data):
        """Determines the winner of the point based on the last event."""
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
        """Ends the current point, updates the game state, and saves data."""
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Nenhum ponto ativo para finalizar!"
            return

        # Adiciona o evento final (Winner/Error) à lista de eventos do ponto
        self.add_event_to_point(event_info)

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
        """Deletes the last recorded point, including those loaded from CSV."""
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
        """Updates the displayed game state to match the current frame."""
        for frame, game_state in reversed(self.game_history):
            if self.current_frame_num >= frame:
                self.display_game = game_state
                return
        self.display_game.reset_match()

    def save_to_csv(self):
        """Delega o salvamento dos dados para o CSVHandler."""
        if not self.all_points_data:
            print("Nenhum ponto foi gravado. Nenhum arquivo CSV será gerado.")
            return
        self.csv_handler.save_csv(self.all_points_data)

    def load_from_csv(self):
        """Delega o carregamento do CSV para o CSVHandler e processa os dados."""
        loaded_points = self.csv_handler.load_csv()
        if not loaded_points:
            print("Nenhum dado carregado do CSV.")
            return

        print(f"Carregando estado do CSV: {OUTPUT_CSV_PATH}")
        self.all_points_data = loaded_points
        self.game.reset_match()
        self.game_history = []

        for point_data in self.all_points_data:
            # Atualiza o estado do jogo com base no último evento do ponto
            last_event = point_data["events"][-1]
            if last_event["event_code"] in ["W", "E"]:
                point_winner = self.point_winnner(point_data)
                self.game.point_won_by(point_winner)
                frame_of_point_end = point_data["events"][-1]["event_frame"]
                self.game_history.append((frame_of_point_end, copy.deepcopy(self.game)))

        # Define o frame atual para o último ponto registrado
        if self.all_points_data:
            # Find the latest frame number among all events
            latest_frame = max(
                event["event_frame"]
                for point in self.all_points_data
                for event in point["events"]
            )

            self.current_frame_num = min(latest_frame, self.total_frames - 1)
            self.point_counter = max([p["point_id"] for p in self.all_points_data], default=0)

            # Ensure seeking is successful
            if not self.vs.seek(self.current_frame_num):
                print(f"Warning: Failed to seek to frame {self.current_frame_num} after loading from CSV.")

            # Read a frame to ensure the stream is correctly positioned and a frame is available
            ret, frame = self.vs.read(self.current_frame_num)
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

        # Ler o frame inicial (seja o 0 ou o carregado do CSV)
        ret, frame = self.vs.read(self.current_frame_num)
        if not ret or frame is None:
            print(f"ERRO CRÍTICO: Não foi possível ler o frame inicial ({self.current_frame_num}). Saindo.")
            return  # Sai do método run se o frame inicial não puder ser carregado
        
        while True:
            loop_start_time = time.time()  # FULL LOOP start time

            read_start_time = time.time()

            processing_times = []  # ADD: create an empty list before the loop
            start_time = time.time()  # START: Mede o tempo de início do loop

            # Attempt to read a frame if not paused or if frame is None (e.g., first frame or after seek)
            if not self.is_paused or frame is None or jump_target != -1: # Added jump_target condition
                if not self.is_paused:
                    # Calculate next frame for playback if not paused
                    self.current_frame_num += self.frame_increment
                    if self.current_frame_num >= self.total_frames:
                        self.current_frame_num = self.total_frames - 1
                else:
                    # If paused and frame is None, retry current frame
                    # Note: In pause, current_frame_num is maintained, no increment
                    next_frame = self.current_frame_num 
                
                # Attempt to read the frame with retries
                retries = 3
                ret, frame = False, None  # Initialize for the loop
                for attempt in range(retries):
                    ret, frame = self.vs.read(self.current_frame_num)
                    if ret and frame is not None:
                        break  # Exit retry loop on success
                    else:
                        print(f"Retry {attempt + 1}/{retries} reading frame {self.current_frame_num}. Ret: {ret}")
                        time.sleep(0.1)  # Short delay before retrying
                 # If reading failed after retries, break the loop
                if not ret or frame is None:
                    print(f"Error: Failed to retrieve frame {self.current_frame_num} after {retries} retries.")
                    break
                read_end_time = time.time()
            else: # If paused and frame is not None, and no jump, no new read is needed
                read_end_time = read_start_time # No new read, so end time is same as start for timing purposes

            self._update_game_for_frame()  # Update game state *before* drawing

            # Always start from a copy of the current frame
            if frame is not None:  # Ensure frame is valid before processing
                display_frame = frame.copy() #copy the original frame

                if scale_percent < 100:
                    width = int(display_frame.shape[1] * scale_percent / 100)
                    height = int(display_frame.shape[0] * scale_percent / 100)
                    display_frame = cv2.resize(display_frame, (width, height), interpolation=cv2.INTER_AREA)

                if self.config["FLIP_VIDEO_CODE"] is not None:
                    display_frame = cv2.flip(display_frame, self.config["FLIP_VIDEO_CODE"])
            else:
                display_frame = None # Handle case where frame is still None after retries

            ui_start_time = time.time()  # START: UI drawing start time
            
            if display_frame is not None: # Ensure valid frame before drawing overlay
                # --- DELEGA O DESENHO PARA O UI HANDLER ---
                self.ui_handler.draw_overlay(
                display_frame,
                current_state=self.current_state,
                is_paused=self.is_paused,
                frame_increment=self.frame_increment,
                last_event_info=self.last_event_info,
                frame_info=f"Frame: {self.current_frame_num}/{self.total_frames}",
            )

            score_data = self.scoreboard_presenter.get_score_data(self.display_game)
            if display_frame is not None: # Ensure valid frame before drawing scoreboard
                self.ui_handler.draw_scoreboard(display_frame, score_data)

                self.ui_handler.show_frame(display_frame) # Always show the UI Frame

            ui_end_time = time.time()  # END: UI drawing end time
            
            # --- CÁLCULO DINÂMICO DO TEMPO DE ESPERA PARA SINCRONIZAÇÃO COM O FPS ---
            wait_start_time = time.time()  # START: Wait time calculation start
            if self.is_paused:
                wait_time = 0  # Pausado, espera indefinidamente por uma tecla
            else:
                # Calcula o tempo que o processamento do frame levou
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Calcula a duração que o frame DEVERIA ter, considerando o avanço (frame_increment)
                target_duration_ms = (1000 / self.fps) * self.frame_increment
                
                # O tempo a esperar é a diferença. Se for negativo, o processamento está atrasado.
                time_to_wait = target_duration_ms - elapsed_ms
                wait_time = max(1, int(time_to_wait))  # Ensure wait_time is at least 1
            key = cv2.waitKey(wait_time) & 0xFF

            if key == ord("x"):
                print("Saindo do analisador.")
                break
            elif key == ord(" "):
                self.is_paused = not self.is_paused
                self.frame_increment = 1
            elif key == ord("p"):
                if not self.is_paused:
                    if self.frame_increment >= 4:
                        self.frame_increment = 1
                    else:
                        self.frame_increment *= 2
            elif key == ord("z"):
                self.is_paused = True
                self.delete_last_point()
            elif key == ord("K"):
                jump_target = self.current_frame_num - 1
            elif key == ord("k"):
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
                target_frame = max(0, min(jump_target, self.total_frames - 1))
                ret, frame = self.vs.read(target_frame)
                if ret:
                    self.current_frame_num = target_frame

                self._update_game_for_frame()
                jump_target = -1

            if key in self.config["KEY_MAPPINGS"]:
                self.is_paused = True
                event_info = self.config["KEY_MAPPINGS"][key]
                action = event_info["action"]

                if action == "START_POINT":
                    self.start_new_point(event_info)  # Já adiciona o primeiro evento
                elif action == "ADD_EVENT":
                    self.add_event_to_point(event_info)
                elif action == "END_POINT":
                    self.end_point(event_info)

            wait_end_time = time.time()  # END: Wait time calculation end
            loop_end_time = time.time()
            read_duration = (read_end_time - read_start_time) * 1000
            ui_duration = (ui_end_time - ui_start_time) * 1000
            wait_duration = (wait_end_time - wait_start_time) * 1000
            full_loop_duration = (loop_end_time - loop_start_time) * 1000
            if not self.is_paused:
                print(
                    f"Read: {read_duration:.2f}ms, UI: {ui_duration:.2f}ms, Wait: {wait_duration:.2f}ms, Full Loop: {full_loop_duration:.2f}ms"
                )

        self.stop_analyzer()


if __name__ == "__main__":
    print("""
    ==================================================================
    Analisador de Tênis Otimizado - Comandos
    ==================================================================
    Controle de Playback:
      - ESPAÇO: Pausar / Continuar
      - p: Acelerar reprodução (1x, 2x, 4x, 8x, ciclo)
      - x: Sair e Salvar

    Navegação (apenas quando pausado):
      - k/K: Frame anterior / seguinte
      - j/l: Pular 10 frames para trás / frente
      - J/L: Pular 3 segundos para trás / frente

    Marcação de Pontos:
      - A/B: Iniciar ponto (Sacador A ou B)
      - 1,2,f,b,d,m,v,s: Registrar golpes
      - e/w: Finalizar ponto (Erro / Winner)
      - z: Apagar último ponto / Cancelar ponto atual
    =================================================================
    """)

    analyzer = TennisVideoAnalyzer(CONFIG)
    analyzer.run()
