import cv2
import time
from threading import Thread, Lock
from queue import Queue


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
            with self.lock:
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
        with self.lock:
            self.stream.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            # Verifica se o frame foi ajustado corretamente
            if self.stream.get(cv2.CAP_PROP_POS_FRAMES) != frame_number:
                raise RuntimeError(f"Falha ao buscar o frame {frame_number}.")
            # Limpa a fila de forma segura
            while not self.Q.empty():
                self.Q.get()

            # Preenche o buffer novamente após o seek
            for _ in range(
                min(self.Q.maxsize, 10)
            ):  # Lê até 10 frames para preencher o buffer
                grabbed, frame = self.stream.read()
                if not grabbed:
                    self.stopped = True
                    break
                self.Q.put(frame)

    def more(self):
        return self.Q.qsize() > 0

    def stop(self):
        self.stopped = True
        self.thread.join()
