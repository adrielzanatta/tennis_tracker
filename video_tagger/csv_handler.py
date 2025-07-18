import pandas as pd
from typing import List, Dict
import os

class CSVHandler:
    """Gerencia a leitura e escrita de arquivos CSV para análise de tênis."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load_csv(self) -> List[Dict]:
        """
        Carrega os dados de um arquivo CSV, se existir, e os agrupa por ponto.
        Retorna uma lista de dicionários, onde cada dicionário representa um ponto.
        """
        try:
            # Garante que as colunas sejam lidas como string para evitar erros de tipo
            df = pd.read_csv(self.csv_path, sep=";", decimal=",", dtype={'event_code': str})
            if df.empty:
                return []
            
            # Agrupa os eventos por 'point_id'
            grouped_points = df.groupby("point_id")
            points = []
            for point_id, events_df in grouped_points:
                # O primeiro evento de um ponto determina o sacador
                server = events_df.iloc[0]["event_code"]
                
                point_data = {
                    "point_id": int(point_id),
                    "server": server,
                    "events": events_df.to_dict("records"),
                }
                points.append(point_data)
            print(f"Análise anterior carregada com sucesso de: {self.csv_path}")
            return points
        except FileNotFoundError:
            print("Nenhum arquivo CSV encontrado. Iniciando uma nova análise.")
            return []
        except Exception as e:
            print(f"Erro ao carregar o arquivo CSV: {e}")
            return []

    def save_csv(self, all_points_data: List[Dict]):
        """
        Salva todos os dados da análise da sessão atual em um arquivo CSV,
        sobrescrevendo qualquer arquivo existente.
        """
        if not all_points_data:
            print("Nenhum ponto foi gravado. Nenhum arquivo CSV será gerado.")
            return

        # Garante que o diretório de saída exista
        output_dir = os.path.dirname(self.csv_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Transforma a lista de pontos em um formato plano para o DataFrame
        flat_data = []
        for point in all_points_data:
            for event in point["events"]:
                # Cria um dicionário para cada evento
                event_row = {
                    "point_id": point["point_id"],
                    # Adiciona os outros campos do evento
                    "event_code": event.get("event_code"),
                    "event_frame": event.get("event_frame"),
                    "event_timestamp_sec": event.get("event_timestamp_sec"),
                }
                flat_data.append(event_row)
        
        if not flat_data:
            print("Nenhum evento para salvar.")
            return

        new_df = pd.DataFrame(flat_data)
        
        # Salva o DataFrame no CSV, sobrescrevendo o arquivo
        try:
            new_df.to_csv(self.csv_path, index=False, sep=";", decimal=",",
                          columns=["point_id", "event_code", "event_frame", "event_timestamp_sec"])
            print(f"Análise salva com sucesso em: {self.csv_path}")
        except Exception as e:
            print(f"Erro ao salvar o arquivo CSV: {e}")