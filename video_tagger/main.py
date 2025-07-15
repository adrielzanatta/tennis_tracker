import cv2
import time
import os
import subprocess
import copy

# Importações dos módulos do projeto
from config import CONFIG, VIDEO_PATH, OUTPUT_CSV_PATH
from video_stream import VideoStream
from scoreboard import Scoreboard
from ui_handler import UIHandler
from csv_handler import CSVHandler
from app_state import AppState
from commands import StartPointCommand, AddEventCommand, EndPointCommand

class TennisVideoAnalyzer:
    def __init__(self, config):
        self.config = config
        self._transcode_video()

        self.window_name = config["WINDOW_NAME"]
        self.csv_handler = CSVHandler(OUTPUT_CSV_PATH)
        self.vs = VideoStream(self.video_path)
        
        print(f"Vídeo carregado com sucesso: {self.video_path}")
        self.total_frames = self.vs.total_frames or 1
        self.fps = self.vs.fps

        # Inicializa o estado centralizado da aplicação
        self.state = AppState(
            config["PLAYER_A_NAME"], 
            config["PLAYER_B_NAME"], 
            self.total_frames
        )
        # Disponibiliza o FPS para o estado, para cálculos de timestamp
        self.state.fps = self.fps

        self.scoreboard_presenter = Scoreboard()
        self.ui_handler = UIHandler(self.window_name)

    def _transcode_video(self):
        """
        Verifica se existe uma versão otimizada do vídeo. Se não, tenta criá-la
        usando ffmpeg. Usa a versão otimizada se disponível.
        """
        original_video_path = VIDEO_PATH
        video_dir = os.path.dirname(original_video_path)
        video_filename = os.path.basename(original_video_path)
        video_name, _ = os.path.splitext(video_filename)

        optimized_video_path = os.path.join(video_dir, f"{video_name}_optimized_720p.mp4")
        self.video_path = original_video_path # Padrão

        if not os.path.exists(optimized_video_path):
            print(f"Versão otimizada não encontrada. Transcodificando '{original_video_path}'...")
            try:
                command = [
                    "ffmpeg", "-i", original_video_path,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "copy", "-vf", "scale=-1:720",
                    optimized_video_path
                ]
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

    def _get_command(self, key):
        """
        Mapeia uma tecla pressionada para um objeto de Comando correspondente.
        Retorna None se a tecla não tiver uma ação de jogo associada.
        """
        if key not in self.config["KEY_MAPPINGS"]:
            return None
        
        self.state.is_paused = True # Pausa o vídeo ao registrar uma ação de jogo
        event_info = self.config["KEY_MAPPINGS"][key]
        action = event_info["action"]

        if action == "START_POINT":
            return StartPointCommand(self.state, event_info)
        elif action == "ADD_EVENT":
            return AddEventCommand(self.state, event_info)
        elif action == "END_POINT":
            return EndPointCommand(self.state, event_info)
        
        return None

    def run(self):
        """
        Inicia e gerencia o loop principal da aplicação.
        """
        scale_percent = self.config.get("ANALYSIS_SCALE_PERCENT", 100)
        
        # Leitura do frame inicial
        ret, frame = self.vs.read_at_frame(self.state.current_frame_num)
        if not ret:
            print("ERRO CRÍTICO: Não foi possível ler o frame inicial. Saindo.")
            return

        while True:
            start_time = time.time()
            
            # --- LÓGICA DE LEITURA DE FRAME ---
            if self.state.jump_target != -1:
                ret, frame = self.vs.read_at_frame(self.state.jump_target)
                if ret:
                    self.state.current_frame_num = self.state.jump_target
                self.state.jump_target = -1
            elif not self.state.is_paused:
                # Pula (frame_increment - 1) frames de forma eficiente
                for _ in range(self.state.frame_increment - 1):
                    self.vs.stream.grab()
                
                # Lê o frame que será realmente exibido
                ret, frame = self.vs.read_sequential()

                if ret:
                    self.state.current_frame_num += self.state.frame_increment
                else:
                    self.state.is_paused = True

            if not ret or frame is None:
                key = cv2.waitKey(0) & 0xFF
                if key == ord('x'):
                    break
                continue

            self.state.update_display_game_for_frame()

            display_frame = frame.copy()
            if scale_percent < 100:
                width = int(display_frame.shape[1] * scale_percent / 100)
                height = int(display_frame.shape[0] * scale_percent / 100)
                display_frame = cv2.resize(display_frame, (width, height), interpolation=cv2.INTER_AREA)

            if self.config["FLIP_VIDEO_CODE"] is not None:
                display_frame = cv2.flip(display_frame, self.config["FLIP_VIDEO_CODE"])

            # --- DELEGA O DESENHO PARA O UI HANDLER ---
            self.ui_handler.draw_overlay(
                display_frame, self.state.current_state, self.state.is_paused,
                self.state.frame_increment, self.state.last_event_info,
                f"Frame: {self.state.current_frame_num}/{self.total_frames}",
            )
            score_data = self.scoreboard_presenter.get_score_data(self.state.display_game)
            self.ui_handler.draw_scoreboard(display_frame, score_data)
            self.ui_handler.show_frame(display_frame)

            # --- CÁLCULO DE ESPERA E CAPTURA DE TECLA (CORRIGIDO) ---
            elapsed_ms = (time.time() - start_time) * 1000
            # O tempo de duração de um frame é sempre baseado no FPS original do vídeo
            target_duration_ms = (1000 / self.fps) if self.fps > 0 else 0
            wait_time = max(1, int(target_duration_ms - elapsed_ms)) if not self.state.is_paused else 0
            
            key = cv2.waitKey(wait_time) & 0xFF
            
            # --- PROCESSAMENTO DOS CONTROLES E COMANDOS ---
            if key == ord("x"):
                break
            elif key == ord(" "):
                self.state.toggle_pause()
            elif key == ord("p"):
                next_increment = self.state.frame_increment * 2
                self.state.set_frame_increment(next_increment if next_increment <= 8 else 1)
            elif key in [ord("k"), ord("K"), ord("j"), ord("l"), ord("J"), ord("L")]:
                jump_amount = {
                    ord("k"): 1, ord("K"): -1,
                    ord("j"): -10, ord("l"): 10,
                    ord("J"): -int(self.fps * 3), ord("L"): int(self.fps * 3)
                }.get(key, 0)
                self.state.set_jump_target(self.state.current_frame_num + jump_amount)
            else:
                command = self._get_command(key)
                if command:
                    command.execute()

        self.stop_analyzer()

    def stop_analyzer(self):
        """Libera os recursos e salva os dados antes de sair."""
        self.vs.stop()
        cv2.destroyAllWindows()
        # self.csv_handler.save_csv(self.state.all_points_data)

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