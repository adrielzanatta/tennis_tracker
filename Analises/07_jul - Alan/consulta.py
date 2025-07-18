import pandas as pd

df = pd.read_csv("C:/github/tennis_tracker/Analises/07_jul - Alan/S1-1_6.csv", sep=";", decimal=",", dtype={'event_code': str})

df = df.groupby("point_id")["event_code"].count()

print(df.sort_values().head(10))