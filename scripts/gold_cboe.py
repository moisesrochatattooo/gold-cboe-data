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
    
    # Data atual para identificar 0DTE (Formato YYMMDD)
    today_str = datetime.now(timezone.utc).strftime("%y%m%d")
    
    parsed_opts = []
    for o in opts:
        opt_str = o.get("option", "")
        if len(opt_str) < 15: continue
        
        opt_date = opt_str[3:9]
        opt_type = opt_str[9] 
        try:
            strike = float(opt_str[-8:]) / 1000.0
        except:
            continue
            
        parsed_opts.append({
            "strike": strike,
            "option_type": opt_type,
            "is_0dte": (opt_date == today_str),
            "open_interest": o.get("open_interest", 0),
            "gamma": o.get("gamma", 0)
        })

    # Filtrar níveis próximos ao preço (ajuda na relevância do gráfico)
    # Pegamos níveis num range de +-15% do spot
    near_opts = [o for o in parsed_opts if spot * 0.85 <= o["strike"] <= spot * 1.15]
    if not near_opts: near_opts = parsed_opts

    # Separar Calls e Puts
    calls = [o for o in near_opts if o["option_type"] == "C"]
    puts = [o for o in near_opts if o["option_type"] == "P"]

    # 0DTE Levels
    calls_0dte = [o for o in calls if o["is_0dte"]]
    puts_0dte = [o for o in puts if o["is_0dte"]]

    # Encontrar as Walls (Maior OI)
    def get_top(arr, n=3):
        return sorted([o for o in arr if o["open_interest"] > 0], 
                      key=lambda x: x["open_interest"], reverse=True)[:n]

    top_levels = []
    
    # 1. Macro Walls (Toda a cadeia perto do spot)
    for o in get_top(calls, 3):
        top_levels.append({"s": o["strike"], "t": "CW", "oi": o["open_interest"]})
    for o in get_top(puts, 3):
        top_levels.append({"s": o["strike"], "t": "PW", "oi": o["open_interest"]})

    # 2. 0DTE Walls (Se existirem)
    if calls_0dte or puts_0dte:
        for o in get_top(calls_0dte, 2):
            top_levels.append({"s": o["strike"], "t": "CW0", "oi": o["open_interest"]})
        for o in get_top(puts_0dte, 2):
            top_levels.append({"s": o["strike"], "t": "PW0", "oi": o["open_interest"]})

    # 3. Estimativa de Gamma Flip (onde Gamma líquida é zero)
    # Agrupar por strike para calcular Gamma Líquida
    gamma_map = {}
    for o in near_opts:
        s = o["strike"]
        if s not in gamma_map: gamma_map[s] = 0
        gamma_map[s] += o["gamma"] if o["option_type"] == "C" else -o["gamma"]
    
    # O strike onde o valor absoluto da Gamma Líquida é menor é o "Flip"
    gamma_flip = 0
    if gamma_map:
        gamma_flip = min(gamma_map.keys(), key=lambda s: abs(gamma_map[s]))
        top_levels.append({"s": gamma_flip, "t": "GF", "oi": 0})

    call_oi = sum(o["open_interest"] for o in calls)
    put_oi = sum(o["open_interest"] for o in puts)
    sentiment = "bullish" if call_oi > put_oi else "bearish"

    return {
        "symbol": NAME, 
        "spot": spot, 
        "sentiment": sentiment,
        "gamma_flip": gamma_flip,
        "top_levels": top_levels,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

def main():
    result = fetch()
    out_path = OUT_DIR / f"{NAME}_latest.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    logging.info("Arquivo atualizado em %s", out_path)

if __name__ == "__main__":
    main()
