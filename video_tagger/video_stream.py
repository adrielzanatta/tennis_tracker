import cv2
import time

class VideoStream:
    """
    Wrapper síncrono para o cv2.VideoCapture, com acesso direto aos frames.
    """

    def __init__(self, path):
        self.stream = cv2.VideoCapture(path)
        if not self.stream.isOpened():
            raise FileNotFoundError(f"Não foi possível abrir o vídeo em: {path}")

        self.total_frames = int(self.stream.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.stream.get(cv2.CAP_PROP_FPS) or 30

    def read(self, frame_number=None):
        """
        Lê um frame do vídeo. Se frame_number for fornecido, pula para esse frame antes de ler.
        Retorna uma tupla (True, frame) se bem-sucedido, (False, None) se o frame não existir.
        """
        overall_start = time.time()
        seek_time = 0
        if frame_number is not None:
            seek_start = time.time()
            if not 0 <= frame_number < self.total_frames:
                return False, None  # Frame fora do intervalo
            if not self.seek(frame_number):
                return False, None  # Falha ao buscar o frame

        ret, frame = self.stream.read()
        overall_end = time.time()
        if frame_number is not None:
            seek_end = time.time()
            seek_time = (seek_end - seek_start) * 1000
        print(f"VideoStream.read(): Overall: {(overall_end - overall_start) * 1000:.2f} ms, Seek: {seek_time:.2f} ms")
        return ret, frame

    def seek(self, frame_number: int) -> bool:
        """
        Pula para um frame específico. Retorna True se bem-sucedido, False caso contrário.
        """
        if not 0 <= frame_number < self.total_frames:
            return False  # Frame fora do intervalo
        self.stream.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        # Verificação mais robusta:
        return int(self.stream.get(cv2.CAP_PROP_POS_FRAMES)) == frame_number

    def stop(self):
        self.stream.release()
