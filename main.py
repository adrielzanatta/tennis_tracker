import cv2
import pandas as pd
import os
import time
from threading import Thread
from queue import Queue
import sys
from threading import Lock

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
OUTPUT_CSV_PATH = f"./{video_name_without_ext}_analisado.csv"
print(f"Arquivo de saída será: {OUTPUT_CSV_PATH}")

CONFIG = {
    # --- JANELA E VÍDEO ---
    "WINDOW_NAME": "Analisador de Golpes - Tênis (Otimizado)",
    "FLIP_VIDEO_CODE": 1,
    # --- OTIMIZAÇÃO DE DESEMPENHO ---
    "ANALYSIS_SCALE_PERCENT": 80,  # Reduz para 30% para análise, muito mais rápido
    "THREAD_QUEUE_SIZE": 256,  # Frames para bufferizar em memória. 128 ou 256 é um bom valor.
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


# =====================================================================================
# 2. CLASSE DE STREAM DE VÍDEO OTIMIZADA (PRODUTOR)
# =====================================================================================
class VideoStream:
    """
    Lê frames de um vídeo em uma thread dedicada para evitar I/O blocking
    na thread principal da GUI, garantindo um playback fluido.
    Versão com Lock para garantir thread-safety.
    """

    def __init__(self, path, queue_size=128):
        self.stream = cv2.VideoCapture(path)
        if not self.stream.isOpened():
            raise FileNotFoundError(f"Não foi possível abrir o vídeo em: {path}")

        self.stopped = False
        self.total_frames = int(self.stream.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.stream.get(cv2.CAP_PROP_FPS) or 30

        self.Q = Queue(maxsize=queue_size)
        self.lock = Lock()  # <--- ADICIONADO: Cria o objeto de lock
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while True:
            # Adquire o lock antes de acessar self.stream
            with self.lock:  # <--- MODIFICADO
                if self.stopped:
                    self.stream.release()
                    return

                # Acessa o stream somente quando o lock está ativo
                (grabbed, frame) = self.stream.read()

            # Processa o resultado fora do lock
            if not self.Q.full():
                if not grabbed:
                    self.stopped = True
                    continue
                self.Q.put(frame)
            else:
                time.sleep(0.01)

    def read(self):
        return self.Q.get()

    def seek(self, frame_number):
        """Pula para um frame específico no vídeo de forma segura."""
        # Adquire o lock antes de acessar self.stream
        with self.lock:  # <--- MODIFICADO
            self.stream.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            # Limpa a fila para remover frames antigos que não serão mais usados
            with self.Q.mutex:
                self.Q.queue.clear()

    def more(self):
        return self.Q.qsize() > 0

    def stop(self):
        self.stopped = True
        self.thread.join()


# =====================================================================================
# 3. SUA CLASSE ANALISADORA, AGORA INTEGRADA COM O VIDEOSTREAM
# =====================================================================================
class TennisVideoAnalyzer:
    def __init__(self, config):
        self.config = config
        self.video_path = VIDEO_PATH
        self.window_name = config["WINDOW_NAME"]

        # Inicializa o VideoStream otimizado em vez do cv2.VideoCapture
        self.vs = VideoStream(self.video_path, config["THREAD_QUEUE_SIZE"])
        self.total_frames = self.vs.total_frames
        self.fps = self.vs.fps
        time.sleep(5.0)  # Espera 2s para o buffer da thread encher um pouco

        self.is_paused = True
        self.current_state = "IDLE"
        self.last_event_info = "Pressione ESPAÇO para iniciar."
        self.current_frame_num = 0
        self.playback_speed = 2

        self.all_points_data = []
        self.current_point_data = None
        self.point_counter = 0

        self._setup_ui()

    # _setup_ui, _draw_overlay (sem alterações)
    def _setup_ui(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def _draw_overlay(self, frame):
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_pos = 40

        def draw_text(text, pos, color=(255, 255, 255), scale=0.7):
            cv2.putText(frame, text, pos, font, scale, color, 1, cv2.LINE_AA)

        status_text = f"ESTADO: {'GRAVANDO PONTO' if self.current_state == 'RECORDING_POINT' else 'AGUARDANDO'}"
        status_color = (
            (0, 0, 255) if self.current_state == "RECORDING_POINT" else (0, 255, 255)
        )

        playback_info = "(PAUSADO)" if self.is_paused else f"({self.playback_speed}x)"
        draw_text(
            f"{status_text} {playback_info}", (20, y_pos), status_color, scale=1.0
        )
        y_pos += 40

        if self.last_event_info:
            draw_text(f"Ultimo: {self.last_event_info}", (20, y_pos), (0, 255, 0))
            y_pos += 40

        frame_info = f"Frame: {self.current_frame_num}/{self.total_frames}"
        draw_text(frame_info, (20, y_pos), (255, 255, 255))

    # Método agora usa o contador de frames da classe, não mais do cv2.VideoCapture
    def _get_current_timestamp(self):
        timestamp_sec = self.current_frame_num / self.fps if self.fps > 0 else 0
        return self.current_frame_num, timestamp_sec

    # start_new_point, add_event_to_point (sem alterações lógicas)
    def start_new_point(self, event_info):
        if self.current_state == "RECORDING_POINT":
            self.last_event_info = "ERRO: Ponto atual precisa ser finalizado!"
            return

        self.point_counter += 1
        frame, timestamp = self._get_current_timestamp()

        self.current_point_data = {"point_id": self.point_counter, "events": []}
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

    # end_point (com correção de bug para calcular duração)
    def end_point(self, event_info):
        if self.current_state != "RECORDING_POINT":
            self.last_event_info = "ERRO: Nenhum ponto ativo para finalizar!"
            return

        # Correção: Calcula a duração do ponto
        start_time = self.current_point_data["events"][0]["timestamp_sec"]
        end_time = self.current_point_data["events"][-1]["timestamp_sec"]
        duration = end_time - start_time

        self.current_point_data["duration_sec"] = duration
        self.all_points_data.append(self.current_point_data)
        self.last_event_info = (
            f"Ponto {self.point_counter} finalizado: {event_info['desc']}"
        )
        print(
            f"--- Ponto {self.point_counter} finalizado. Duração: {duration:.2f}s ---"
        )
        self.current_state = "IDLE"
        self.current_point_data = None

    # delete_last_point, save_to_csv (sem alterações lógicas)
    def delete_last_point(self):
        if self.current_state == "RECORDING_POINT":
            point_num_to_cancel = self.current_point_data["point_id"]
            self.current_state = "IDLE"
            self.current_point_data = None
            self.point_counter -= 1
            self.last_event_info = (
                f"Ponto {point_num_to_cancel} em andamento foi cancelado."
            )
            print(f"--- Ponto {point_num_to_cancel} em andamento foi CANCELADO. ---")
            return

        if self.all_points_data:
            deleted_point = self.all_points_data.pop()
            self.point_counter -= 1
            self.last_event_info = f"Ponto {deleted_point['point_id']} foi APAGADO."
            print(
                f"--- Último ponto concluído (Ponto {deleted_point['point_id']}) foi APAGADO. ---"
            )
        else:
            self.last_event_info = "Nenhum ponto para apagar."
            print("--- Nenhum ponto concluído para apagar. ---")

    def save_to_csv(self):
        if not self.all_points_data:
            print("Nenhum ponto foi gravado. Nenhum arquivo CSV será gerado.")
            return

        output_data = []
        for point in self.all_points_data:
            for event in point["events"]:
                output_data.append(
                    {
                        "point_id": point["point_id"],
                        "event_timestamp_sec": event["timestamp_sec"],
                        "event_frame": event["frame"],
                        "event_code": event["event_code"],
                    }
                )
        df = pd.DataFrame(output_data)
        df.to_csv(OUTPUT_CSV_PATH, index=False, sep=";", decimal=",")
        print(f"Análise salva com sucesso em: {OUTPUT_CSV_PATH}")

    def stop_analyzer(self):
        """Rotina para fechar a aplicação de forma segura."""
        self.vs.stop()
        cv2.destroyAllWindows()
        self.save_to_csv()

    # LOOP PRINCIPAL TOTALMENTE REFATORADO PARA ALTA PERFORMANCE
    def run(self):
        scale_percent = self.config.get("ANALYSIS_SCALE_PERCENT", 100)
        frame = None
        jump_target = -1

        while True:
            # Pega o frame mais recente se não estiver pausado ou se for o primeiro frame
            if not self.is_paused or frame is None:
                if self.vs.stopped and not self.vs.more():
                    break  # Fim do vídeo

                # Avança o número de frames de acordo com a velocidade
                for _ in range(self.playback_speed):
                    if self.vs.more():
                        frame = self.vs.read()
                        self.current_frame_num += 1
                    else:
                        break

            # Garante que temos um frame para exibir
            if frame is None:
                break

            # Faz uma cópia para desenhar o overlay sem afetar o frame original
            display_frame = frame.copy()

            # Otimização de Desempenho (redimensionamento)
            if scale_percent < 100:
                width = int(display_frame.shape[1] * scale_percent / 100)
                height = int(display_frame.shape[0] * scale_percent / 100)
                display_frame = cv2.resize(
                    display_frame, (width, height), interpolation=cv2.INTER_AREA
                )

            if self.config["FLIP_VIDEO_CODE"] is not None:
                display_frame = cv2.flip(display_frame, self.config["FLIP_VIDEO_CODE"])

            self._draw_overlay(display_frame)
            cv2.imshow(self.window_name, display_frame)

            # --- Lógica de Controle com waitKey Otimizado ---
            wait_time = 1 if not self.is_paused else 0
            key = cv2.waitKey(wait_time) & 0xFF

            # SAIR
            if key == ord("x"):
                break
            # PAUSE/PLAY
            elif key == ord(" "):
                self.is_paused = not self.is_paused
                self.playback_speed = 1  # Reseta a velocidade ao pausar/despausar
            # APAGAR PONTO
            elif key == ord("z"):
                self.is_paused = True
                self.delete_last_point()

            # NAVEGAÇÃO (só funciona quando pausado para precisão)

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
                self.vs.seek(self.current_frame_num)  # Delega a busca para a thread
                frame = self.vs.read()  # Pega o frame imediatamente após o pulo
                jump_target = -1

            # PROCESSAMENTO DE EVENTOS DE JOGO
            if key in self.config["KEY_MAPPINGS"]:
                self.is_paused = True  # Pausa automaticamente para precisão
                event_info = self.config["KEY_MAPPINGS"][key]
                action = event_info["action"]

                if action == "START_POINT":
                    self.start_new_point(event_info)
                    self.add_event_to_point(event_info)
                elif action == "ADD_EVENT":
                    self.add_event_to_point(event_info)
                elif action == "END_POINT":
                    self.add_event_to_point(event_info)
                    self.end_point(event_info)

        self.stop_analyzer()


# =====================================================================================
# 4. PONTO DE ENTRADA DA APLICAÇÃO
# =====================================================================================
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
