import pandas as pd
from tools import calculate_games

FILE_PATH = "Analises/03_jul - Guilherme/S1-6_3.csv"
df = pd.read_csv(FILE_PATH, sep=";")

# Group by 'point_id', 'server', 'point_start_time_sec', 'point_end_time_sec'
# and concatenate both 'event_frame' and 'event_code' as strings
df["event_code"] = df["event_code"].astype(str)
df["event_frame"] = df["event_frame"].astype(str)
result = (
    df.groupby(["point_id", "server", "point_start_time_sec", "point_end_time_sec"])
    .agg({"event_frame": lambda x: ",".join(x), "event_code": lambda x: "".join(x)})
    .reset_index()
)
result["frame_start"] = result["event_frame"].apply(lambda x: x.split(",")[0])
result["frame_end"] = result["event_frame"].apply(lambda x: x.split(",")[-1])
result["point_id"] = result["point_id"].astype(int)
result.sort_values(by=["point_id", "point_start_time_sec"], inplace=True)

# Concatenate server and event_code
result["server_event_codes"] = result["server"] + result["event_code"]

print(result.head())

calculate_games(result["server_event_codes"].tolist())
