import cv2
from typing import Dict
import numpy as np


class UIHandler:
    """Gerencia a interface do usuário, incluindo o desenho do placar e sobreposição."""

    def __init__(self, window_name: str):
        self.window_name = window_name
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def draw_overlay(
        self,
        frame,
        current_state: str,
        is_paused: bool,
        frame_increment: int,
        last_event_info: str,
        frame_info: str,
    ):
        """Desenha a sobreposição de informações no frame."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_pos = 30

        def draw_text(text, pos, color=(255, 255, 255), scale=0.7):
            cv2.putText(frame, text, pos, font, scale, color, 2, cv2.LINE_AA)

        status_text = f"ESTADO: {'GRAVANDO PONTO' if current_state == 'RECORDING_POINT' else 'AGUARDANDO'}"
        status_color = (
            (0, 255, 0) if current_state == "RECORDING_POINT" else (0, 255, 255)
        )
        playback_info = "(PAUSADO)" if is_paused else f"({frame_increment}x)"
        draw_text(f"{status_text} {playback_info}", (20, y_pos), status_color, scale=1.0)
        y_pos += 40

        if last_event_info:
            draw_text(f"Ultimo: {last_event_info}", (20, y_pos), (50, 205, 255), scale=0.8)
            y_pos += 40

        draw_text(frame_info, (20, y_pos), (255, 255, 255))

    def draw_scoreboard(self, frame, score_data: Dict):
        """Desenha o placar no frame."""
        WIMBLEDON_GREEN = (44, 88, 0)
        WHITE = (255, 255, 255)
        YELLOW = (0, 255, 255)
        FONT = cv2.FONT_HERSHEY_DUPLEX

        frame_h, frame_w, _ = frame.shape
        board_h = 85
        board_w = 450
        start_x = 20
        start_y = frame_h - board_h - 20

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

        if score_data.get("match_over"):
            winner_text = f"VENCEDOR: {score_data['winner']}"
            (w, h), _ = cv2.getTextSize(winner_text, FONT, 0.8, 2)
            text_x = start_x + (board_w - w) // 2
            text_y = start_y + (board_h + h) // 2
            cv2.putText(
                frame, winner_text, (text_x, text_y), FONT, 0.8, YELLOW, 2, cv2.LINE_AA
            )
            return

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

    def show_frame(self, frame):
        """Exibe o frame na janela."""
        if frame is not None and isinstance(frame, np.ndarray):
            # Garante que o tipo de dados é uint8, que é o que o cv2.imshow espera.
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            cv2.imshow(self.window_name, frame)
        # else: # Opcional: Adicionar um log para depuração
        #     print("UIHandler.show_frame recebeu um frame None ou inválido.")
