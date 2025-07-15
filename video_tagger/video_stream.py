import cv2

class VideoStream:
    """
    Wrapper síncrono para o cv2.VideoCapture com leitura otimizada.
    """
    def __init__(self, path):
        self.stream = cv2.VideoCapture(path)
        if not self.stream.isOpened():
            raise FileNotFoundError(f"Não foi possível abrir o vídeo em: {path}")

        self.total_frames = int(self.stream.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.stream.get(cv2.CAP_PROP_FPS) or 30

    def read_sequential(self):
        """
        Lê o próximo frame sequencialmente. Mais rápido para playback.
        Retorna (True, frame) ou (False, None).
        """
        return self.stream.read()

    def read_at_frame(self, frame_number):
        """
        Pula para um frame específico e o lê. Mais lento, use para saltos.
        Retorna (True, frame) ou (False, None).
        """
        if not 0 <= frame_number < self.total_frames:
            return False, None  # Frame fora do intervalo
        
        self.stream.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        current_pos = int(self.stream.get(cv2.CAP_PROP_POS_FRAMES))
        
        # A busca pode não ser precisa, então lemos até chegar lá, se necessário
        if current_pos != frame_number:
            # Se a diferença for grande, a busca falhou de forma mais séria
            if abs(current_pos - frame_number) > 10:
                 print(f"Alerta: Falha ao buscar precisamente o frame {frame_number}. Posição atual: {current_pos}")
                 return False, None
        
        return self.stream.read()

    def stop(self):
        """Libera o recurso de vídeo."""
        self.stream.release()