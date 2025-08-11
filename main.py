from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import pandas as pd, csv, os

app = FastAPI()
CSV_FILE = "prices.csv"

@app.get("/price/latest")
def get_latest_price():
    if not os.path.exists(CSV_FILE):
        raise HTTPException(404, "Fichier CSV non trouvé")
    with open(CSV_FILE, "r", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise HTTPException(404, "Aucune donnée disponible")
    last = rows[-1]
    return {"timestamp": last["timestamp"], "symbol": last["symbol"], "price": float(last["price"])}

@app.get("/price/ohlc")
def get_ohlc(interval: str = Query("1min")):
    df = pd.read_csv("prices.csv")
    df = df[df["timestamp"].str.contains(r"\d{4}-\d{2}-\d{2}")]
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["timestamp","price"]).set_index("timestamp")

    ohlc = df["price"].resample(interval).ohlc().dropna().reset_index()

    # Indicateurs
    ohlc["sma_5"]  = ohlc["close"].rolling(5).mean()
    ohlc["sma_10"] = ohlc["close"].rolling(10).mean()
    ohlc["ema_5"]  = ohlc["close"].ewm(span=5, adjust=False).mean()
    ohlc["ema_10"] = ohlc["close"].ewm(span=10, adjust=False).mean()

    os.makedirs("ohlc", exist_ok=True)
    filename = f"ohlc/ohlc_{interval.replace(' ', '_')}.csv"
    ohlc.to_csv(filename, index=False)

    return [
        {
            "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "open": round(row["open"],2),
            "high": round(row["high"],2),
            "low": round(row["low"],2),
            "close": round(row["close"],2),
            "sma_5": None if pd.isna(row["sma_5"]) else round(row["sma_5"],2),
            "sma_10": None if pd.isna(row["sma_10"]) else round(row["sma_10"],2),
            "ema_5": None if pd.isna(row["ema_5"]) else round(row["ema_5"],2),
            "ema_10": None if pd.isna(row["ema_10"]) else round(row["ema_10"],2),
        } for _, row in ohlc.iterrows()
    ]
