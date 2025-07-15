class Scoreboard:
    """
    Formata os dados de um objeto TennisGame para exibição.
    É uma classe de apresentação (Presenter) e não contém estado próprio.
    """

    def __init__(self):
        self.point_map = {0: "0", 1: "15", 2: "30", 3: "40"}

    def get_score_data(self, game):
        """
        Recebe um objeto TennisGame e retorna um dicionário com os dados
        formatados para serem desenhados na tela.
        """
        if game.match_over:
            return {"match_over": True, "winner": game.winner}

        pA, pB = game.scores["A"], game.scores["B"]

        if game.is_tiebreak or game.is_super_tiebreak:
            pA_pts, pB_pts = str(pA["points"]), str(pB["points"])
        else:
            if pA["points"] >= 3 and pB["points"] >= 3:
                if pA["points"] == pB["points"]:
                    pA_pts, pB_pts = "40", "40"
                elif pA["points"] > pB["points"]:
                    pA_pts, pB_pts = "AD", ""
                else:
                    pA_pts, pB_pts = "", "AD"
            else:
                pA_pts = self.point_map.get(pA["points"])
                pB_pts = self.point_map.get(pB["points"])

        data = {
            "match_over": False,
            "pA": {
                "name": game.player_names["A"],
                "sets_hist": [s[0] for s in game.sets_history],
                "games": pA["games"],
                "points_str": pA_pts,
                "is_server": game.server == "A",
            },
            "pB": {
                "name": game.player_names["B"],
                "sets_hist": [s[1] for s in game.sets_history],
                "games": pB["games"],
                "points_str": pB_pts,
                "is_server": game.server == "B",
            },
        }
        return data
