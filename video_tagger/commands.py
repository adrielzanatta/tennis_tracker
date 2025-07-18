from abc import ABC, abstractmethod
from game_logic import determine_winner # Importa a lógica centralizada
import copy

class Command(ABC):
    """Interface para os comandos executáveis."""
    def __init__(self, app_state):
        self.app_state = app_state

    @abstractmethod
    def execute(self):
        pass

class StartPointCommand(Command):
    def __init__(self, app_state, event_info):
        super().__init__(app_state)
        self.event_info = event_info

    def execute(self):
        if self.app_state.current_state == "RECORDING_POINT":
            self.app_state.last_event_info = "ERRO: Ponto atual precisa ser finalizado!"
            return

        self.app_state.point_counter += 1
        frame = self.app_state.current_frame_num
        timestamp = frame / self.app_state.fps if self.app_state.fps > 0 else 0

        self.app_state.current_player = self.event_info["code"]
        self.app_state.current_point_data = {
            "point_id": self.app_state.point_counter,
            "events": [],
        }
        self.app_state.current_state = "RECORDING_POINT"
        self.app_state.last_event_info = f"Ponto {self.app_state.point_counter} iniciado. Sacador: {self.event_info['desc']}"
        
        # Adiciona o evento de início
        AddEventCommand(self.app_state, self.event_info).execute()

class AddEventCommand(Command):
    def __init__(self, app_state, event_info):
        super().__init__(app_state)
        self.event_info = event_info

    def execute(self):
        if self.app_state.current_state != "RECORDING_POINT":
            self.app_state.last_event_info = "ERRO: Inicie um ponto primeiro (A ou B)!"
            return

        frame = self.app_state.current_frame_num
        timestamp = frame / self.app_state.fps if self.app_state.fps > 0 else 0
        
        self.app_state.current_point_data["events"].append({
            "event_code": self.event_info["code"],
            "event_timestamp_sec": timestamp,
            "event_frame": frame,
        })
        self.app_state.last_event_info = f"Golpe: {self.event_info['desc']}"
        # Alterna o jogador para o próximo golpe
        self.app_state.current_player = "B" if self.app_state.current_player == "A" else "A"

class EndPointCommand(Command):
    def __init__(self, app_state, event_info):
        super().__init__(app_state)
        self.event_info = event_info

    def execute(self):
        if self.app_state.current_state != "RECORDING_POINT":
            self.app_state.last_event_info = "ERRO: Nenhum ponto ativo para finalizar!"
            return
        
        AddEventCommand(self.app_state, self.event_info).execute()
        
        # Usa a função de lógica centralizada
        point_winner = determine_winner(self.app_state.current_point_data)
        
        self.app_state.game.point_won_by(point_winner)
        self.app_state.add_point_to_history()
        
        self.app_state.all_points_data.append(self.app_state.current_point_data)
        self.app_state.last_event_info = f"Ponto {self.app_state.point_counter} finalizado: {self.event_info['desc']}"
        
        self.app_state.reset_current_point()

    def _determine_winner(self):
        point_data = self.app_state.current_point_data
        server = point_data["events"][0]["event_code"]
        receiver = "B" if server == "A" else "A"
        num_shots = len(point_data["events"])
        last_shot_by_server = num_shots % 2 == 1
        last_event_code = point_data["events"][-1]["event_code"]

        if last_event_code == "W":  # Winner
            return server if last_shot_by_server else receiver
        else:  # Error ("E")
            return receiver if last_shot_by_server else server
        
class DeleteLastPointCommand(Command):
    """
    Comando para apagar o último ponto registrado (destrutivo).
    """
    def execute(self):
        if self.app_state.current_state == "RECORDING_POINT":
            # Cancela o ponto em andamento
            self.app_state.reset_current_point(cancelled=True)
            print("--- Ponto em andamento foi CANCELADO. ---")
            return

        if not self.app_state.all_points_data:
            self.app_state.last_event_info = "Nenhum ponto para apagar."
            print("--- Nenhum ponto concluído para apagar. ---")
            return
        
        # Apaga o último ponto e seu histórico
        deleted_point = self.app_state.all_points_data.pop()
        if self.app_state.game_history:
            self.app_state.game_history.pop()

        self.app_state.point_counter -= 1
        
        # Recalcula todo o estado do jogo do zero para garantir consistência
        self.app_state.game.reset_match()
        self.app_state.game_history = []
        for point_data in self.app_state.all_points_data:
            winner = determine_winner(point_data)
            if winner:
                self.app_state.game.point_won_by(winner)
                frame_of_point_end = point_data["events"][-1]["event_frame"]
                self.app_state.game_history.append((frame_of_point_end, copy.deepcopy(self.app_state.game)))

        self.app_state.last_event_info = f"Ponto {deleted_point['point_id']} foi APAGADO."
        print(f"--- Último ponto (Ponto {deleted_point['point_id']}) foi APAGADO. O placar foi recalculado. ---")
