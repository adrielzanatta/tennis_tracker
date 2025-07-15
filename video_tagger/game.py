class TennisGame:
    """
    Gerencia o estado e as regras de uma partida de tênis, incluindo pontos,
    games, sets e tie-breaks. Esta classe é o "cérebro" da partida.
    """

    def __init__(self, player_a_name="A", player_b_name="B"):
        self.player_names = {"A": player_a_name, "B": player_b_name}
        self.reset_match()

    def reset_match(self):
        """Reseta o estado para o início de uma nova partida."""
        self.scores = {
            "A": {"points": 0, "games": 0, "sets": 0},
            "B": {"points": 0, "games": 0, "sets": 0},
        }
        self.sets_history = []
        self.server = "A"
        self.is_tiebreak = False
        self.is_super_tiebreak = False
        self.match_over = False
        self.winner = None

    def point_won_by(self, player_code):
        """Lógica principal que atualiza o estado do jogo quando um jogador ganha um ponto."""
        if self.match_over:
            return

        if self.is_tiebreak or self.is_super_tiebreak:
            self._handle_tiebreak_point(player_code)
        else:
            self._handle_regular_point(player_code)

    def _handle_regular_point(self, player_code):
        """Processa um ponto em um game normal."""
        opponent_code = "B" if player_code == "A" else "A"
        self.scores[player_code]["points"] += 1

        player_points = self.scores[player_code]["points"]
        opponent_points = self.scores[opponent_code]["points"]

        if player_points >= 4 and (player_points - opponent_points) >= 2:
            self._win_game(player_code)

    def _win_game(self, player_code):
        """Processa a vitória de um game."""
        self.scores[player_code]["games"] += 1
        self.scores["A"]["points"] = 0
        self.scores["B"]["points"] = 0
        self.server = "B" if self.server == "A" else "A"

        player_games = self.scores[player_code]["games"]
        opponent_games = self.scores["B" if player_code == "A" else "A"]["games"]

        if player_games >= 6 and (player_games - opponent_games) >= 2:
            self._win_set(player_code)
        elif player_games == 6 and opponent_games == 6:
            self.is_tiebreak = True

    def _win_set(self, player_code):
        """Processa a vitória de um set."""
        self.scores[player_code]["sets"] += 1
        self.sets_history.append((self.scores["A"]["games"], self.scores["B"]["games"]))
        self.scores["A"]["games"] = 0
        self.scores["B"]["games"] = 0
        self.is_tiebreak = False
        self.is_super_tiebreak = False

        if self.scores["A"]["sets"] == 1 and self.scores["B"]["sets"] == 1:
            self.is_super_tiebreak = True

        if self.scores[player_code]["sets"] == 2:
            self.match_over = True
            self.winner = self.player_names[player_code]

    def _handle_tiebreak_point(self, player_code):
        """Processa um ponto dentro de um tie-break (normal ou super)."""
        self.scores[player_code]["points"] += 1

        total_points = self.scores["A"]["points"] + self.scores["B"]["points"]
        if total_points > 0 and total_points % 2 == 1:
            self.server = "B" if self.server == "A" else "A"

        player_points = self.scores[player_code]["points"]
        opponent_points = self.scores["B" if player_code == "A" else "A"]["points"]

        point_target = 10 if self.is_super_tiebreak else 7
        if player_points >= point_target and (player_points - opponent_points) >= 2:
            self.scores[player_code]["games"] += 1
            self._win_set(player_code)
