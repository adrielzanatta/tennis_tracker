import copy
from game import TennisGame

class AppState:
    """
    Gerencia todo o estado da sessão de análise de vídeo.
    Isso inclui o estado da reprodução, os dados dos pontos e o estado do jogo.
    """
    def __init__(self, player_a_name: str, player_b_name: str, total_frames: int):
        self.is_paused = True
        self.current_frame_num = 0
        self.frame_increment = 1
        self.jump_target = -1
        
        self.total_frames = total_frames
        self.last_event_info = "Pressione ESPAÇO para iniciar."
        self.current_state = "IDLE"

        self.all_points_data = []
        self.current_point_data = None
        self.point_counter = 0

        # --- LÓGICA DO JOGO ---
        self.game = TennisGame(player_a_name, player_b_name)
        self.game_history = []
        # Jogo para exibição, sincronizado com o frame
        self.display_game = TennisGame(player_a_name, player_b_name)
        self.current_player = None

    def toggle_pause(self):
        """Alterna o estado de pausa."""
        self.is_paused = not self.is_paused
        if not self.is_paused:
            self.frame_increment = 1 # Reseta a velocidade ao continuar

    def set_frame_increment(self, increment: int):
        """Define a velocidade de reprodução."""
        if not self.is_paused:
            self.frame_increment = increment

    def set_jump_target(self, frame_num: int):
        """Define um alvo para pular no vídeo."""
        self.is_paused = True # Pausa ao pular
        self.jump_target = max(0, min(frame_num, self.total_frames - 1))

    def update_display_game_for_frame(self):
        """
        Atualiza o estado do placar a ser exibido para corresponder
        ao frame atual do vídeo.
        """
        for frame, game_state in reversed(self.game_history):
            if self.current_frame_num >= frame:
                self.display_game = game_state
                return
        # Se nenhum estado for encontrado, reseta para o início
        self.display_game.reset_match()

    def add_point_to_history(self):
        """
        Salva o estado atual do jogo no histórico, associado ao frame
        final do ponto.
        """
        frame_of_point_end = self.current_frame_num
        self.game_history.append((frame_of_point_end, copy.deepcopy(self.game)))

    def reset_current_point(self, cancelled: bool = False):
        """Reseta as informações do ponto atual."""
        if cancelled and self.current_point_data:
            point_num = self.current_point_data.get("point_id", self.point_counter)
            self.last_event_info = f"Ponto {point_num} em andamento foi cancelado."
            self.point_counter -= 1
        
        self.current_state = "IDLE"
        self.current_point_data = None
        self.current_player = None