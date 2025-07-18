import cv2
import time
import os
import subprocess
import copy
import argparse # Importa a biblioteca de argumentos

# Importações dos módulos do projeto
from config import CONFIG
from video_stream import VideoStream
from scoreboard import Scoreboard
from ui_handler import UIHandler
from csv_handler import CSVHandler
from app_state import AppState
from commands import StartPointCommand, AddEventCommand, EndPointCommand, DeleteLastPointCommand
from game_logic import determine_winner

class TennisVideoAnalyzer:
    def __init__(self, config, args):
        self.config = config
        self.args = args # Armazena todos os argumentos da linha de comando

        self._transcode_video()

        self.window_name = config["WINDOW_NAME"]
        self.csv_handler = CSVHandler(self.args.output_csv_path)
        self.vs = VideoStream(self.video_path)
        
        self.total_frames = self.vs.total_frames or 1
        self.fps = self.vs.fps

        self.state = AppState(
            # Usa os nomes dos jogadores fornecidos como argumento
            player_a_name=self.args.player_a, 
            player_b_name=self.args.player_b, 
            total_frames=self.total_frames,
            initial_server=self.args.server
        )
        self.state.fps = self.fps
        self.scoreboard_presenter = Scoreboard()
        self.ui_handler = UIHandler(self.window_name)

    def _transcode_video(self):
        original_video_path = self.args.video_path
        video_dir = os.path.dirname(original_video_path)
        video_filename = os.path.basename(original_video_path)
        video_name, _ = os.path.splitext(video_filename)
        optimized_video_path = os.path.join(video_dir, f"{video_name}_optimized_720p.mp4")
        self.video_path = original_video_path

        if not os.path.exists(optimized_video_path):
            print(f"Versão otimizada não encontrada. Transcodificando...")
            try:
                command = ["ffmpeg", "-i", original_video_path, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "copy", "-vf", "scale=-1:720", optimized_video_path]
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                self.video_path = optimized_video_path
            except Exception as e:
                print(f"\nERRO ao transcodificar: {e}\nContinuando com o vídeo original.\n")
        else:
            self.video_path = optimized_video_path
        print(f"Usando vídeo: {self.video_path}")

    def _get_command(self, key):
        if key in self.config["KEY_MAPPINGS"]:
            self.state.is_paused = True
            event_info = self.config["KEY_MAPPINGS"][key]
            action = event_info["action"]
            if action == "START_POINT": return StartPointCommand(self.state, event_info)
            if action == "ADD_EVENT": return AddEventCommand(self.state, event_info)
            if action == "END_POINT": return EndPointCommand(self.state, event_info)
        return None

    def load_from_csv(self):
        loaded_points = self.csv_handler.load_csv()
        if not loaded_points: return

        self.state.all_points_data = loaded_points
        self.state.game.reset_match()
        self.state.game_history = []

        for point_data in self.state.all_points_data:
            winner = determine_winner(point_data)
            if winner:
                self.state.game.point_won_by(winner)
                frame_of_point_end = point_data["events"][-1]["event_frame"]
                self.state.game_history.append((frame_of_point_end, copy.deepcopy(self.state.game)))
        
        if self.state.all_points_data:
            latest_frame = max(event["event_frame"] for p in self.state.all_points_data for event in p["events"])
            self.state.current_frame_num = min(latest_frame, self.total_frames - 1)
            self.state.point_counter = max((p["point_id"] for p in self.state.all_points_data), default=0)
            self.state.last_event_info = f"Carregado do CSV. {len(self.state.all_points_data)} pontos."
            print(f"Estado carregado. Iniciando do frame {self.state.current_frame_num}.")

    def run(self):
        scale_percent = self.args.scale # Usa a escala fornecida como argumento
        self.load_from_csv()
        ret, frame = self.vs.read_at_frame(self.state.current_frame_num)
        if not ret:
            print("ERRO CRÍTICO: Não foi possível ler o frame inicial. Saindo.")
            return

        while True:
            start_time = time.time()
            if self.state.jump_target != -1:
                ret, frame = self.vs.read_at_frame(self.state.jump_target)
                if ret: self.state.current_frame_num = self.state.jump_target
                self.state.jump_target = -1
            elif not self.state.is_paused:
                for _ in range(self.state.frame_increment - 1): self.vs.stream.grab()
                ret, frame = self.vs.read_sequential()
                if ret: self.state.current_frame_num += self.state.frame_increment
                else: self.state.is_paused = True

            if not ret or frame is None:
                key = cv2.waitKey(0) & 0xFF
                if key == ord('x'): break
                continue

            self.state.update_display_game_for_frame()

            display_frame = frame.copy()
            if scale_percent < 100:
                width = int(display_frame.shape[1] * scale_percent / 100)
                height = int(display_frame.shape[0] * scale_percent / 100)
                display_frame = cv2.resize(display_frame, (width, height), interpolation=cv2.INTER_AREA)
            
            # Usa o código de flip fornecido como argumento
            if self.args.flip is not None:
                display_frame = cv2.flip(display_frame, self.args.flip)

            self.ui_handler.draw_overlay(display_frame, self.state.current_state, self.state.is_paused, self.state.frame_increment, self.state.last_event_info, f"Frame: {self.state.current_frame_num}/{self.total_frames}")
            score_data = self.scoreboard_presenter.get_score_data(self.state.display_game)
            self.ui_handler.draw_scoreboard(display_frame, score_data)
            self.ui_handler.show_frame(display_frame)

            elapsed_ms = (time.time() - start_time) * 1000
            target_duration_ms = (1000 / self.fps) if self.fps > 0 else 0
            wait_time = max(1, int(target_duration_ms - elapsed_ms)) if not self.state.is_paused else 0
            key = cv2.waitKey(wait_time) & 0xFF
            
            if key == ord("x"): break
            elif key == ord(" "): self.state.toggle_pause()
            elif key == ord("p"):
                next_increment = self.state.frame_increment * 2
                self.state.set_frame_increment(next_increment if next_increment <= 8 else 1)
            elif key in [ord("k"), ord("K"), ord("j"), ord("l"), ord("J"), ord("L")]:
                jump_map = {ord("k"): 1, ord("K"): -1, ord("j"): -10, ord("l"): 10, ord("J"): -int(self.fps * 3), ord("L"): int(self.fps * 3)}
                self.state.set_jump_target(self.state.current_frame_num + jump_map.get(key, 0))
            elif key == ord("z"):
                DeleteLastPointCommand(self.state).execute()
            else:
                command = self._get_command(key)
                if command: command.execute()

        self.stop_analyzer()

    def stop_analyzer(self):
        self.csv_handler.save_csv(self.state.all_points_data)
        self.vs.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analisador de Tênis Otimizado.", formatter_class=argparse.RawTextHelpFormatter)
    
    # --- NOVOS ARGUMENTOS ---
    parser.add_argument("video_path", help="Caminho para o arquivo de vídeo a ser analisado.")
    parser.add_argument("--server", choices=["A", "B"], default="A", help="Jogador que inicia sacando (A ou B). Padrão: A")
    parser.add_argument("--player_a", default="JOGADOR A", help="Nome do Jogador A. Padrão: 'JOGADOR A'")
    parser.add_argument("--player_b", default="JOGADOR B", help="Nome do Jogador B. Padrão: 'JOGADOR B'")
    parser.add_argument("--scale", type=int, default=100, help="Escala do vídeo em %% para análise (ex: 50). Padrão: 60")
    parser.add_argument("--flip", type=int, choices=[0, 1], help="Inverter vídeo verticalmente (0) ou horizontalmente (1).")
    
    args = parser.parse_args()

    # Gera o caminho de saída do CSV dinamicamente
    video_filename = os.path.basename(args.video_path)
    video_name_without_ext = os.path.splitext(video_filename)[0]
    output_csv_dir = "Analises/temp"
    os.makedirs(output_csv_dir, exist_ok=True)
    # Adiciona o caminho ao objeto 'args' para fácil acesso
    args.output_csv_path = os.path.join(output_csv_dir, f"{video_name_without_ext}_analisado.csv")

    print("""
    ==================================================================
    Analisador de Tênis Otimizado - Comandos
    ==================================================================
    (Comandos de execução agora disponíveis. Use -h para ver as opções)
    ==================================================================
    """)

    # Instancia e executa o analisador com todos os argumentos
    analyzer = TennisVideoAnalyzer(config=CONFIG, args=args)
    analyzer.run()