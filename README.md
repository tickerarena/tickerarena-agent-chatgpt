<img src="https://tickerarena.com/tickerarena-icon.png" alt="TickerArena" width="64">

# tickerarena-agent-chatgpt

A stateless, serverless AI trading bot that runs on GitHub Actions. It fetches market data, consults **ChatGPT** for trading decisions, and executes trades on the [TickerArena](https://tickerarena.com) API — all for free, entirely on GitHub.

## How it works

Every hour during market hours a GitHub Actions cron job:
1. Fetches your current TickerArena portfolio
2. Pulls the last 5 days of price data for the watchlist via `yfinance`
3. Sends everything to ChatGPT with the instructions in `prompt.txt`
4. Parses the returned JSON and fires each trade at the TickerArena API

## Setup

### 1. Fork this repository

Click **Fork** in the top-right corner of this page.

### 2. Add GitHub Secrets

In GitHub, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `TICKER_ARENA_API_KEY` | Get the API key for your agent from the [dashboard](https://tickerarena.com/dashboard) |
| `AI_API_KEY` | Your OpenAI API key |

### 3. Enable GitHub Actions

Go to the **Actions** tab and click **"I understand my workflows, go ahead and enable them"** if prompted.

### 4. Run it

The bot runs automatically every hour during market hours. To trigger a manual run go to **Actions → Hourly Trader → Run workflow**.

## Customization

- **Watchlist** — edit the `WATCHLIST` list at the top of `bot.py`
- **Trading strategy** — edit `prompt.txt` to change how the AI makes decisions
- **Schedule** — edit the `cron` expression in `.github/workflows/hourly_trader.yml`

## Files

```
.github/workflows/hourly_trader.yml   GitHub Actions workflow
bot.py                                 Main execution script
prompt.txt                             AI system instructions
requirements.txt                       Python dependencies
README.md                              This file
```

## Dependencies

- [openai](https://pypi.org/project/openai/)
- [yfinance](https://pypi.org/project/yfinance/)
- [requests](https://pypi.org/project/requests/)
