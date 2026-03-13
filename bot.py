import json
import os
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

import yfinance as yf
from openai import OpenAI
from tickerarena import TickerArena, TickerArenaAPIError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TICKER_ARENA_API_KEY = os.getenv("TICKER_ARENA_API_KEY")
AI_API_KEY = os.getenv("AI_API_KEY")

if not TICKER_ARENA_API_KEY or not AI_API_KEY:
    print("ERROR: TICKER_ARENA_API_KEY and AI_API_KEY must be set.")
    sys.exit(1)

WATCHLIST = ["AAPL", "NVDA", "TSLA", "BTC-USD"]

ta = TickerArena(api_key=TICKER_ARENA_API_KEY)


# ---------------------------------------------------------------------------
# Market hours guard (NYSE: 9:30am-4:00pm ET, DST-aware)
# ---------------------------------------------------------------------------
def is_market_open() -> bool:
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    return time(9, 30) <= now.time() < time(16, 0)

# ---------------------------------------------------------------------------
# Step 1: Load prompt
# ---------------------------------------------------------------------------
def load_prompt() -> str:
    with open("prompt.md", "r") as f:
        return f.read().strip()


# ---------------------------------------------------------------------------
# Step 2: Fetch portfolio
# ---------------------------------------------------------------------------
def fetch_portfolio() -> dict:
    try:
        port = ta.portfolio()
        return {
            "positions": [
                {
                    "tradeId": p.trade_id,
                    "ticker": p.ticker,
                    "direction": p.direction,
                    "allocation": p.allocation,
                    "roiPercent": p.roi_percent,
                    "enteredAt": p.entered_at,
                }
                for p in port.positions
            ],
            "totalAllocated": port.total_allocated,
        }
    except TickerArenaAPIError as e:
        print(f"WARNING: Could not fetch portfolio ({e}). Using empty portfolio.")
        return {"positions": [], "totalAllocated": 0}


# ---------------------------------------------------------------------------
# Step 3: Fetch market data
# ---------------------------------------------------------------------------
def fetch_market_data() -> dict:
    market_data = {}
    for ticker in WATCHLIST:
        try:
            data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
            if len(data) >= 2:
                latest_close = float(data["Close"].iloc[-1].item())
                prev_close = float(data["Close"].iloc[-2].item())
                trend = "UP" if latest_close >= prev_close else "DOWN"
                market_data[ticker] = {
                    "latest_close": round(latest_close, 2),
                    "trend": trend,
                }
            else:
                print(f"WARNING: Insufficient data for {ticker}.")
        except Exception as e:
            print(f"WARNING: Could not fetch data for {ticker} ({e}).")
    return market_data


# ---------------------------------------------------------------------------
# Step 4: Ask ChatGPT for trading decisions
# ---------------------------------------------------------------------------
def get_ai_decisions(system_prompt: str, portfolio: dict, market_data: dict) -> list:
    client = OpenAI(api_key=AI_API_KEY)

    user_prompt = json.dumps(
        {"current_portfolio": portfolio, "market_data": market_data},
        indent=2,
    )

    response = client.chat.completions.create(
        model="gpt-5.4",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    try:
        # Try direct load first
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        # Fallback: Try to extract JSON from markdown fences or look for the first '{' and last '}'
        try:
            import re
            json_match = re.search(r"(\{.*\})", content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(1))
            else:
                print(f"ERROR: AI returned invalid content: {content[:100]}...")
                return []
        except Exception:
            print("ERROR: AI failed to return valid JSON. Skipping trades.")
            return []

    return parsed.get("trades", [])


# ---------------------------------------------------------------------------
# Step 5: Execute trades
# ---------------------------------------------------------------------------
def execute_trades(trades: list) -> None:
    if not trades:
        print("No trades to execute.")
        return

    for trade in trades:
        ticker = trade.get("ticker")
        action = trade.get("action")
        percent = trade.get("percent")

        if not ticker or not action or percent is None:
            print(f"Skipping malformed trade: {trade}")
            continue

        print(f"Executing trade: ticker={ticker} action={action} percent={percent}")
        try:
            ta.trade(ticker=ticker, action=action, percent=int(percent))
            print(f"  OK")
        except TickerArenaAPIError as e:
            print(f"  ERROR executing trade for {ticker}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=== Ticker Arena ChatGPT Agent ===")
    if not is_market_open():
        print("Market is closed. Exiting.")
        sys.exit(0)


    system_prompt = load_prompt()
    print("Prompt loaded.")

    portfolio = fetch_portfolio()
    print(f"Portfolio fetched: {json.dumps(portfolio)}")

    market_data = fetch_market_data()
    print(f"Market data: {json.dumps(market_data)}")

    print("Requesting trading decisions from GPT-5.4...")
    trades = get_ai_decisions(system_prompt, portfolio, market_data)
    print(f"Decisions received: {json.dumps(trades)}")

    execute_trades(trades)
    print("=== Done ===")


if __name__ == "__main__":
    main()
