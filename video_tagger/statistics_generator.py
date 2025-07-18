import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
from collections import defaultdict

class StatisticsGenerator:
    """
    Generates a detailed statistical report from a tennis match CSV file.
    """
    def __init__(self, csv_path: str, player_a: str, player_b: str):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Analysis file not found: {csv_path}")
        
        self.df = pd.read_csv(csv_path, sep=";", dtype=str)
        self.df['point_id'] = pd.to_numeric(self.df['point_id'], errors='coerce')
        self.df.dropna(subset=['point_id'], inplace=True)

        self.csv_path = csv_path
        
        self.stats = {}
        for player_code, player_name in [('A', player_a), ('B', player_b)]:
            self.stats[player_code] = {
                'name': player_name,
                'total_points_played': 0,
                'points_won': 0,
                'points_won_serving': 0,
                'points_won_receiving': 0,
                'winners_by_stroke': defaultdict(int),
                'errors_forced_by_stroke': defaultdict(int), # Renamed for clarity
                'aces': 0,
                'double_faults': 0,
                'serves_total': 0,
                '1st_serves_in': 0,
                '2nd_serves_in': 0,
                '1st_serve_pts_won': 0,
                '2nd_serve_pts_won': 0,
                'return_pts_won_vs_1st_serve': 0,
                'return_pts_won_vs_2nd_serve': 0
            }

    def _determine_winner_and_server(self, point_events):
        """Determines the server and winner of a point from its events."""
        server = point_events.iloc[0]['event_code']
        receiver = 'B' if server == 'A' else 'A'
        
        rally_events = point_events.iloc[1:]
        if rally_events.empty: return None, server
        
        last_event = rally_events.iloc[-1]
        num_shots_in_rally = len(rally_events)
        
        # **BUG FIX 1**: The logic for who hit the last shot was inverted.
        # 1 shot (serve) -> server. 2 shots (serve, return) -> receiver.
        # An odd number of shots means the server hit last.
        last_player_is_server = (num_shots_in_rally % 2 == 0)

        if last_event['event_code'] == 'W': winner = server if last_player_is_server else receiver
        elif last_event['event_code'] == 'E': winner = receiver if last_player_is_server else server
        else: winner = None
            
        return winner, server

    def _calculate_stats(self):
        """Processes each point to calculate the full set of statistics."""
        points = self.df.groupby('point_id')
        
        for _, point_df in points:
            winner, server = self._determine_winner_and_server(point_df)
            if not winner: continue

            loser = 'B' if winner == 'A' else 'A'
            receiver = loser if server == winner else winner

            self.stats['A']['total_points_played'] += 1
            self.stats['B']['total_points_played'] += 1
            
            self.stats[winner]['points_won'] += 1
            if winner == server: self.stats[winner]['points_won_serving'] += 1
            else: self.stats[winner]['points_won_receiving'] += 1
                
            rally_events = point_df.iloc[1:]
            if rally_events.empty: continue
            
            serve_type = rally_events.iloc[0]['event_code']
            self.stats[server]['serves_total'] += 1

            if serve_type == '1':
                self.stats[server]['1st_serves_in'] += 1
                if winner == server: self.stats[server]['1st_serve_pts_won'] += 1
                else: self.stats[receiver]['return_pts_won_vs_1st_serve'] += 1
            elif serve_type == '2':
                self.stats[server]['2nd_serves_in'] += 1
                if winner == server: self.stats[server]['2nd_serve_pts_won'] += 1
                else: self.stats[receiver]['return_pts_won_vs_2nd_serve'] += 1
                    
            last_event = rally_events.iloc[-1]
            # A point must have at least a serve and an outcome (W/E) to have a stroke.
            if len(rally_events) == 2:
                if serve_type == '1':
                    self.stats[server]['aces'] += 1
                    
                elif serve_type == '2':
                    self.stats[server]['double_faults'] += 1
                    
            if len(rally_events) > 2:
                stroke_event = rally_events.iloc[-2]['event_code']
                
                if last_event['event_code'] == 'W':
                    self.stats[winner]['winners_by_stroke'][stroke_event] += 1
                    # Check for Ace: 1st serve, winner, exactly 2 events in rally (serve + W)
                   
                elif last_event['event_code'] == 'E':
                    self.stats[winner]['errors_forced_by_stroke'][stroke_event] += 1
   
    def _format_dict_stats(self, stats_dict):
        """Formats a dictionary of stats into a readable string."""
        if not stats_dict: return "0"
        return ", ".join([f"{k}: {v}" for k, v in stats_dict.items()])

    def generate_report(self):
        """Generates and prints the complete, formatted report."""
        self._calculate_stats()
        
        report = f"\n--- Relatório Estatístico da Partida ---\n"
        report += f"{self.stats['A']['name']} vs. {self.stats['B']['name']}\n"
        
        for code in ['A', 'B']:
            p_stats = self.stats[code]
            s_stats = p_stats
            receiver_code = 'B' if code == 'A' else 'A'
            opp_s_stats = self.stats[receiver_code]

            report += "\n" + "="*50 + "\n"
            report += f" JOGADOR: {p_stats['name']}\n"
            report += "="*50 + "\n"
            
            report += "\n-- PONTOS --\n"
            total_played = p_stats['total_points_played']
            win_perc = (p_stats['points_won'] / total_played * 100) if total_played > 0 else 0
            report += f"- Pontos Ganhos: {p_stats['points_won']} de {total_played} ({win_perc:.1f}%)\n"
            report += f"- Pontos sacando: {p_stats['points_won_serving']}\n"
            report += f"- Pontos recebendo: {p_stats['points_won_receiving']}\n"
            report += f"- Winners: {self._format_dict_stats(p_stats['winners_by_stroke'])}\n"
            # **CLARITY FIX**: Changed label to avoid confusion. An error for player X is a point for player Y.
            report += f"- Erros: {self._format_dict_stats(p_stats['errors_forced_by_stroke'])}\n"
            
            report += "\n-- SAQUE --\n"
            report += f"- Aces: {s_stats['aces']}\n"
            report += f"- Duplas Faltas: {s_stats['double_faults']}\n"
            if s_stats['1st_serves_in'] > 0:
                perc = (s_stats['1st_serve_pts_won'] / s_stats['1st_serves_in'] * 100)
                report += f"- % Pontos Ganhos 1º Saque: {perc:.1f}% ({s_stats['1st_serve_pts_won']}/{s_stats['1st_serves_in']})\n"
            if s_stats['2nd_serves_in'] > 0:
                perc = (s_stats['2nd_serve_pts_won'] / s_stats['2nd_serves_in'] * 100)
                report += f"- % Pontos Ganhos 2º Saque: {perc:.1f}% ({s_stats['2nd_serve_pts_won']}/{s_stats['2nd_serves_in']})\n"
            
            report += "\n-- DEVOLUÇÃO --\n"
            report += f"- Pontos Ganhos na Devolução: {p_stats['points_won_receiving']}\n"
            if opp_s_stats['1st_serves_in'] > 0:
                perc = (p_stats['return_pts_won_vs_1st_serve'] / opp_s_stats['1st_serves_in'] * 100)
                report += f"- % Pontos Ganhos vs 1º Saque: {perc:.1f}% ({p_stats['return_pts_won_vs_1st_serve']}/{opp_s_stats['1st_serves_in']})\n"
            if opp_s_stats['2nd_serves_in'] > 0:
                perc = (p_stats['return_pts_won_vs_2nd_serve'] / opp_s_stats['2nd_serves_in'] * 100)
                report += f"- % Pontos Ganhos vs 2º Saque: {perc:.1f}% ({p_stats['return_pts_won_vs_2nd_serve']}/{opp_s_stats['2nd_serves_in']})\n"


        print(report)
        return report

    def plot_summary_chart(self):
        pass # Deactivated for now

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Estatísticas Detalhadas de Partida de Tênis.")
    parser.add_argument("csv_path", help="Caminho para o arquivo CSV gerado pela análise.")
    parser.add_argument("--player_a", default="JOGADOR A", help="Nome do Jogador A.")
    parser.add_argument("--player_b", default="JOGADOR B", help="Nome do Jogador B.")
    args = parser.parse_args()
    try:
        stats_generator = StatisticsGenerator(
            csv_path=args.csv_path,
            player_a=args.player_a,
            player_b=args.player_b
        )
        stats_generator.generate_report()
    except FileNotFoundError as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")