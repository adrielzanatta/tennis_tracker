import pandas as pd
from typing import List, Dict


class CSVHandler:
    """Gerencia a leitura e escrita de arquivos CSV para análise de tênis."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load_csv(self) -> List[Dict]:
        """Carrega os dados do CSV e retorna uma lista de pontos."""
        try:
            df = pd.read_csv(self.csv_path, sep=";", decimal=",")
            if df.empty:
                return []
            grouped_points = df.groupby("point_id")
            points = []
            for point_id, events in grouped_points:
                point_data = {
                    "point_id": point_id,
                    "server": events.iloc[0]["event_code"],
                    "events": events.to_dict("records"),
                }
                points.append(point_data)
            return points
        except FileNotFoundError:
            return []

    def save_csv(self, points: List[Dict]):
        """Salva os dados no CSV, preservando os existentes."""
        try:
            existing_df = pd.read_csv(self.csv_path, sep=";", decimal=",")
        except FileNotFoundError:
            existing_df = pd.DataFrame()

        new_data = []
        for point in points:
            for event in point["events"]:
                new_data.append(
                    {
                        "point_id": point["point_id"],
                        "event_code": event["event_code"],
                        "event_frame": event["event_frame"],
                        "event_timestamp_sec": event["event_timestamp_sec"],
                    }
                )
        new_df = pd.DataFrame(new_data)
        combined_df = (
            pd.concat([existing_df, new_df]).drop_duplicates().reset_index(drop=True)
        )
        combined_df.to_csv(self.csv_path, index=False, sep=";", decimal=",")
