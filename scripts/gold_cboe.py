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
    return {"symbol": NAME, "spot": spot, "options": opts, "generated_at": datetime.now(timezone.utc).isoformat()}

def main():
    result = fetch()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"{NAME}_{ts}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    logging.info("Arquivo salvo em %s", out_path)

if __name__ == "__main__":
    main()
