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
    
    parsed_opts = []
    for o in opts:
        opt_str = o.get("option", "")
        if len(opt_str) < 15: continue
        
        # GLD YYMMDD C/P Strike(8 digits)
        # GLD is 3 chars. 3 + 6 (date) = 9. Index 9 is C/P
        opt_type = opt_str[9] 
        try:
            # Strike is last 8 digits, divided by 1000
            strike = float(opt_str[-8:]) / 1000.0
        except:
            continue
            
        parsed_opts.append({
            "strike": strike,
            "option_type": opt_type,
            "open_interest": o.get("open_interest", 0)
        })

    # Cálculo de Sentimento e Níveis (Walls)
    call_options = [o for o in parsed_opts if o["option_type"] == "C"]
    put_options = [o for o in parsed_opts if o["option_type"] == "P"]

    call_oi = sum(o["open_interest"] for o in call_options)
    put_oi = sum(o["open_interest"] for o in put_options)

    # Identifica as "Walls" (Strikes com maior OI)
    c_with_oi = [o for o in call_options if o["open_interest"] > 0]
    p_with_oi = [o for o in put_options if o["open_interest"] > 0]

    call_wall = max(c_with_oi, key=lambda x: x["open_interest"], default={}).get("strike", spot)
    put_wall = max(p_with_oi, key=lambda x: x["open_interest"], default={}).get("strike", spot)

    # Top 5 Calls e Top 5 Puts por OI
    top_calls = sorted(c_with_oi, key=lambda x: x["open_interest"], reverse=True)[:5]
    top_puts = sorted(p_with_oi, key=lambda x: x["open_interest"], reverse=True)[:5]
    
    top_levels = []
    for o in top_calls:
        top_levels.append({"s": o["strike"], "t": "C", "oi": o["open_interest"]})
    for o in top_puts:
        top_levels.append({"s": o["strike"], "t": "P", "oi": o["open_interest"]})

    sentiment = "neutral"
    if call_oi > put_oi * 1.1: sentiment = "bullish"
    elif put_oi > call_oi * 1.1: sentiment = "bearish"

    return {
        "symbol": NAME, 
        "spot": spot, 
        "sentiment": sentiment,
        "call_wall": call_wall,
        "put_wall": put_wall,
        "top_levels": top_levels,
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
