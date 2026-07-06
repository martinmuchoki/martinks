# NSE Signal Bot V10.1 - Autonomous Strategy Factory

## Features
- Automatically generates trading strategies
- Backtests every strategy across all stocks
- Builds a strategy leaderboard
- Scores strategies using return, Sharpe, win rate and drawdown
- AI strategy improvement ideas
- Downloadable strategy leaderboard
- Downloadable strategy report
- Cloud-ready deployment files:
  - Procfile
  - runtime.txt
  - requirements.txt

## Run locally
Double-click:

START_BOT_V10_1.bat

Then open:

http://127.0.0.1:5000

## Deploy to Render
Build command:

pip install -r requirements.txt

Start command:

gunicorn app:app

This is a decision-support system only. It does not automatically trade on Ziidi.
