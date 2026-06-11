#!/usr/bin/env python3
import json, os, time, logging, requests
from pathlib import Path
from datetime import datetime, timezone

# Configurações
CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
SYMBOL = "GLD"
NAME = "GLD"
OUT_DIR = Path(__file__).parent.parent / "api" / "dados"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

def fetch():
    url = CBOE_URL.format(symbol=SYMBOL)
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()["data"]
    spot = data.get("current_price")
    opts = data.get("options", [])
    
    # Cálculo de Sentimento e Níveis (Walls)
    call_options = [o for o in opts if o.get("option_type") == "C"]
    put_options = [o for o in opts if o.get("option_type") == "P"]

    call_oi = sum(o.get("open_interest", 0) for o in call_options)
    put_oi = sum(o.get("open_interest", 0) for o in put_options)

    # Identifica as "Walls" (Strikes com maior OI)
    call_wall = max(call_options, key=lambda x: x.get("open_interest", 0), default={}).get("strike", 0)
    put_wall = max(put_options, key=lambda x: x.get("open_interest", 0), default={}).get("strike", 0)

    sentiment = "neutral"
    if call_oi > put_oi * 1.1: sentiment = "bullish"
    elif put_oi > call_oi * 1.1: sentiment = "bearish"

    return {
        "symbol": NAME, 
        "spot": spot, 
        "sentiment": sentiment,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def main():
    result = fetch()
    out_path = OUT_DIR / f"{NAME}_latest.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    logging.info("Arquivo atualizado em %s", out_path)

if __name__ == "__main__":
    main()
