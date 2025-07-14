import unittest
from game import TennisGame


class TestTennisGame(unittest.TestCase):
    """
    Conjunto de testes para a classe TennisGame, garantindo que a lógica de
    pontuação do tênis seja implementada corretamente.
    """

    def setUp(self):
        """
        Este método é executado antes de cada teste, garantindo que cada
        teste comece com uma instância limpa do jogo.
        """
        self.game = TennisGame("Player A", "Player B")

    def _win_points(self, player, num_points):
        """Função auxiliar para simular um jogador ganhando vários pontos."""
        for _ in range(num_points):
            self.game.point_won_by(player)

    def _win_games(self, player, num_games):
        """Função auxiliar para simular um jogador ganhando vários games."""
        for _ in range(num_games):
            self._win_points(player, 4)

    def test_initial_state(self):
        """Testa se o jogo começa com a pontuação zerada."""
        self.assertEqual(self.game.scores["A"]["points"], 0)
        self.assertEqual(self.game.scores["A"]["games"], 0)
        self.assertEqual(self.game.scores["A"]["sets"], 0)
        self.assertFalse(self.game.match_over)
        self.assertEqual(self.game.server, "A")

    def test_point_scoring(self):
        """Testa a pontuação básica dentro de um game."""
        self._win_points("A", 1)
        self.assertEqual(self.game.scores["A"]["points"], 1)  # 15
        self._win_points("A", 1)
        self.assertEqual(self.game.scores["A"]["points"], 2)  # 30
        self._win_points("B", 1)
        self.assertEqual(self.game.scores["B"]["points"], 1)  # 15
        self._win_points("A", 1)
        self.assertEqual(self.game.scores["A"]["points"], 3)  # 40

    def test_win_game_and_server_change(self):
        """Testa a vitória de um game e a subsequente troca de sacador."""
        self._win_points("A", 4)
        self.assertEqual(self.game.scores["A"]["games"], 1)
        self.assertEqual(self.game.scores["A"]["points"], 0)
        self.assertEqual(self.game.scores["B"]["points"], 0)
        self.assertEqual(self.game.server, "B")

    def test_deuce_and_advantage(self):
        """Testa a lógica de deuce e vantagem."""
        self._win_points("A", 3)
        self._win_points("B", 3)
        # Pontuação deve ser 3-3 (Deuce)
        self.assertEqual(self.game.scores["A"]["points"], 3)
        self.assertEqual(self.game.scores["B"]["points"], 3)

        # Jogador A ganha um ponto (Vantagem A)
        self._win_points("A", 1)
        self.assertEqual(self.game.scores["A"]["points"], 4)
        self.assertEqual(self.game.scores["B"]["points"], 3)

        # Jogador B ganha um ponto (Deuce novamente)
        self._win_points("B", 1)
        self.assertEqual(self.game.scores["A"]["points"], 4)
        self.assertEqual(self.game.scores["B"]["points"], 4)

        # Jogador A ganha dois pontos para vencer o game
        self._win_points("A", 2)
        self.assertEqual(self.game.scores["A"]["games"], 1)
        self.assertEqual(self.game.scores["A"]["points"], 0)

    def test_win_set(self):
        """Testa a vitória de um set."""
        self._win_games("A", 5)
        self._win_games("B", 4)
        self.assertEqual(self.game.scores["A"]["games"], 5)
        self.assertEqual(self.game.scores["B"]["games"], 4)

        # Jogador A ganha o game decisivo para o set
        self._win_games("A", 1)
        self.assertEqual(self.game.scores["A"]["sets"], 1)
        self.assertEqual(self.game.scores["A"]["games"], 0)  # Games resetam
        self.assertEqual(self.game.scores["B"]["games"], 0)
        self.assertEqual(self.game.sets_history, [(6, 4)])

    def test_tiebreak(self):
        """Testa a ativação e a pontuação de um tie-break normal."""
        self._win_games("A", 5)
        self._win_games("B", 6)
        self._win_games("A", 1)  # Placar de games: 6-6

        self.assertTrue(self.game.is_tiebreak)
        self.assertFalse(self.game.is_super_tiebreak)

        # Jogador A vence o tie-break por 7-5
        self._win_points("A", 6)
        self._win_points("B", 5)
        self.assertEqual(self.game.scores["A"]["points"], 6)
        self._win_points("A", 1)

        self.assertEqual(self.game.scores["A"]["sets"], 1)
        self.assertFalse(self.game.is_tiebreak)
        self.assertEqual(self.game.sets_history, [(7, 6)])

    def test_super_tiebreak_and_match_win(self):
        """Testa a ativação de um super tie-break e a vitória da partida."""
        # Set 1: A vence por 6-4
        self._win_games("B", 4)
        self._win_games("A", 6)

        # Set 2: B vence por 7-5
        self._win_games("A", 5)
        self._win_games("B", 7)

        self.assertEqual(self.game.scores["A"]["sets"], 1)
        self.assertEqual(self.game.scores["B"]["sets"], 1)

        # Leva ao super tie-break
        self.assertTrue(self.game.is_super_tiebreak)

        # Jogador B vence o super tie-break por 10-8
        self._win_points("A", 8)
        self._win_points("B", 10)

        self.assertEqual(self.game.scores["B"]["sets"], 2)
        self.assertTrue(self.game.match_over)
        self.assertEqual(self.game.winner, "Player B")


if __name__ == "__main__":
    unittest.main()
