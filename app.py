
from flask import Flask, render_template_string, send_file
from pathlib import Path
import pandas as pd, numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
import os

app=Flask(__name__)
DATA=Path("prices.csv")
MASTER=Path("symbol_master.csv")
LEADERBOARD=Path("strategy_leaderboard_v10_1.csv")
REPORT=Path("strategy_factory_report_v10_1.txt")

CSS='body{font-family:Arial;margin:22px;background:#eef5f0}h1,h2{color:#0f5f35}.note{background:#fff3cd;padding:12px;border-left:5px solid #ffc107;margin:14px 0}.cards{display:flex;gap:12px;flex-wrap:wrap}.card{background:white;padding:14px 18px;border-radius:10px;box-shadow:0 1px 6px #bbb;min-width:190px}.card b{font-size:22px;color:#0f5f35}.button{background:#0f5f35;color:white;padding:10px 13px;border-radius:7px;text-decoration:none;display:inline-block;margin:5px 5px 12px 0}table{border-collapse:collapse;width:100%;background:white;margin-bottom:20px}th,td{border:1px solid #ddd;padding:8px;text-align:center;font-size:12px}th{background:#0f5f35;color:white}pre{white-space:pre-wrap;background:white;padding:15px;border-radius:9px}.PASS{color:green;font-weight:bold}.FAIL{color:red;font-weight:bold}.WATCH{color:#b8860b;font-weight:bold}'

def load_prices():
    df=pd.read_csv(DATA)
    df["date"]=pd.to_datetime(df["date"])
    df["symbol"]=df["symbol"].astype(str).str.upper().str.strip()
    for c in ["open","high","low","close","volume"]:
        df[c]=pd.to_numeric(df[c],errors="coerce")
    return df.dropna().sort_values(["symbol","date"])

def indicators(g):
    g=g.sort_values("date").copy()
    g["ret"]=g.close.pct_change().fillna(0)
    g["ma10"]=g.close.rolling(10,min_periods=1).mean()
    g["ma20"]=g.close.rolling(20,min_periods=1).mean()
    g["ma50"]=g.close.rolling(50,min_periods=1).mean()
    d=g.close.diff()
    gain=d.where(d>0,0).rolling(14,min_periods=1).mean()
    loss=-d.where(d<0,0).rolling(14,min_periods=1).mean()
    rs=gain/loss.replace(0,np.nan)
    g["rsi"]=(100-(100/(1+rs))).fillna(50)
    g["breakout"]=g.close > g.high.rolling(20,min_periods=1).max().shift(1)
    g["vol_avg"]=g.volume.rolling(20,min_periods=1).mean()
    return g

STRATEGIES=[
    {"name":"MA Trend Rider","description":"Buy when MA20 > MA50 and price above MA20; sell when price falls below MA20."},
    {"name":"RSI Recovery","description":"Buy when RSI recovers above 40 from oversold area; sell above 70."},
    {"name":"Breakout Volume","description":"Buy 20-day breakout with volume above average; sell when price loses MA20."},
    {"name":"Defensive Momentum","description":"Buy when price above MA50 and RSI between 45 and 65; sell below MA50."},
    {"name":"Fast MA Cross","description":"Buy MA10 > MA20; sell MA10 < MA20."}
]

def signal_for_strategy(g, strategy):
    if strategy=="MA Trend Rider":
        return np.where((g.ma20>g.ma50)&(g.close>g.ma20),"BUY",np.where(g.close<g.ma20,"SELL","HOLD"))
    if strategy=="RSI Recovery":
        return np.where((g.rsi>40)&(g.rsi.shift(1)<=40),"BUY",np.where(g.rsi>70,"SELL","HOLD"))
    if strategy=="Breakout Volume":
        return np.where((g.breakout)&(g.volume>g.vol_avg),"BUY",np.where(g.close<g.ma20,"SELL","HOLD"))
    if strategy=="Defensive Momentum":
        return np.where((g.close>g.ma50)&(g.rsi>=45)&(g.rsi<=65),"BUY",np.where(g.close<g.ma50,"SELL","HOLD"))
    if strategy=="Fast MA Cross":
        return np.where(g.ma10>g.ma20,"BUY",np.where(g.ma10<g.ma20,"SELL","HOLD"))
    return "HOLD"

def max_drawdown(equity):
    s=pd.Series(equity)
    peak=s.cummax()
    dd=(s-peak)/peak
    return abs(dd.min())*100 if len(dd) else 0

def backtest_strategy_symbol(strategy, sym, capital=10000):
    df=load_prices()
    g=indicators(df[df.symbol==sym].copy()).reset_index(drop=True)
    g["signal"]=signal_for_strategy(g,strategy)
    cash=capital; shares=0; entry=0; wins=losses=0; gp=gl=0; equity=[]
    trades=0
    for _,row in g.iterrows():
        price=float(row.close)
        if shares==0 and row.signal=="BUY":
            shares=int(cash//price)
            if shares>0:
                cash-=shares*price; entry=price
        elif shares>0 and row.signal=="SELL":
            profit=(price-entry)*shares
            cash+=shares*price
            trades+=1
            if profit>=0: wins+=1; gp+=profit
            else: losses+=1; gl+=abs(profit)
            shares=0
        equity.append(cash+shares*price)
    final=equity[-1] if equity else capital
    returns=pd.Series(equity).pct_change().dropna()
    sharpe=(returns.mean()/returns.std()*np.sqrt(252)) if len(returns)>2 and returns.std()!=0 else 0
    total_trades=wins+losses
    win_rate=wins/total_trades*100 if total_trades else 0
    pf=gp/gl if gl else (gp if gp else 0)
    return {"strategy":strategy,"symbol":sym,"final_equity":round(final,2),"return_pct":round((final/capital-1)*100,2),"trades":trades,"win_rate":round(win_rate,2),"profit_factor":round(pf,2),"sharpe":round(sharpe,2),"max_drawdown":round(max_drawdown(equity),2)}

def strategy_factory():
    syms=sorted(load_prices().symbol.unique())
    rows=[]
    for s in STRATEGIES:
        strat=s["name"]
        results=[backtest_strategy_symbol(strat, sym) for sym in syms]
        avg_return=np.mean([r["return_pct"] for r in results])
        avg_sharpe=np.mean([r["sharpe"] for r in results])
        avg_dd=np.mean([r["max_drawdown"] for r in results])
        avg_win=np.mean([r["win_rate"] for r in results])
        score=max(0,min(100,50+avg_return+avg_sharpe*8-avg_dd*.5+avg_win*.15))
        status="PASS" if score>=65 else "WATCH" if score>=50 else "FAIL"
        best=sorted(results,key=lambda x:x["return_pct"],reverse=True)[:3]
        rows.append({"strategy":strat,"description":s["description"],"score":round(score,1),"status":status,"avg_return":round(avg_return,2),"avg_sharpe":round(avg_sharpe,2),"avg_drawdown":round(avg_dd,2),"avg_win_rate":round(avg_win,2),"best_symbols":", ".join([b["symbol"] for b in best])})
    rows=sorted(rows,key=lambda x:x["score"],reverse=True)
    pd.DataFrame(rows).to_csv(LEADERBOARD,index=False)
    return rows

def all_strategy_results(strategy):
    syms=sorted(load_prices().symbol.unique())
    return sorted([backtest_strategy_symbol(strategy,sym) for sym in syms],key=lambda x:x["return_pct"],reverse=True)

def ai_generate_strategy_ideas():
    leaders=strategy_factory()
    ideas=[]
    for i,s in enumerate(leaders[:3],1):
        ideas.append({"idea":f"AI Strategy Idea {i}","base_strategy":s["strategy"],"improvement":f"Focus on {s['best_symbols']} and avoid stocks with drawdown above {s['avg_drawdown']}%","priority":"HIGH" if s["status"]=="PASS" else "MEDIUM"})
    ideas.append({"idea":"Hybrid Strategy","base_strategy":"MA Trend Rider + Breakout Volume","improvement":"Only enter when trend and breakout agree","priority":"HIGH"})
    return ideas

def report_text():
    leaderboard=strategy_factory()
    ideas=ai_generate_strategy_ideas()
    txt=["NSE V10.1 AUTONOMOUS STRATEGY FACTORY REPORT",f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",""]
    txt.append("Strategy Leaderboard:")
    for s in leaderboard:
        txt.append(f"- {s['strategy']} | Score {s['score']} | {s['status']} | Return {s['avg_return']}% | Sharpe {s['avg_sharpe']} | Best: {s['best_symbols']}")
    txt.append("")
    txt.append("AI Strategy Ideas:")
    for i in ideas:
        txt.append(f"- {i['idea']}: {i['base_strategy']} | {i['improvement']} | {i['priority']}")
    txt.append("")
    txt.append("Cloud-ready files included: Procfile, runtime.txt, requirements.txt")
    REPORT.write_text("\n".join(txt),encoding="utf-8")
    return "\n".join(txt)

def chart_html():
    rows=strategy_factory()
    fig=go.Figure()
    fig.add_trace(go.Bar(x=[r["strategy"] for r in rows],y=[r["score"] for r in rows],name="Strategy Score"))
    fig.add_trace(go.Scatter(x=[r["strategy"] for r in rows],y=[r["avg_return"] for r in rows],mode="lines+markers",name="Avg Return %"))
    fig.update_layout(title="V10.1 Strategy Leaderboard",height=520,template="plotly_white")
    return pio.to_html(fig,full_html=False,include_plotlyjs="cdn")

def page(title,body):
    return f"<!doctype html><html><head><title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>"

@app.route("/")
def index():
    rows=strategy_factory()
    body=render_template_string("""
<h1>NSE Signal Bot V10.1 — Autonomous Strategy Factory</h1>
<div class='note'>Generate, backtest, rank, and report trading strategies automatically. Cloud-ready for Render deployment.</div>
<a class='button' href='/leaderboard'>Strategy Leaderboard</a><a class='button' href='/ideas'>AI Strategy Ideas</a><a class='button' href='/strategy/MA Trend Rider'>Strategy Detail</a><a class='button' href='/report'>Strategy Report</a><a class='button' href='/download_report'>Download Report</a><a class='button' href='/download_leaderboard'>Download Leaderboard</a>
<div class='cards'>
<div class='card'>Best Strategy<br><b>{{rows[0].strategy}}</b></div>
<div class='card'>Score<br><b>{{rows[0].score}}</b></div>
<div class='card'>Status<br><b>{{rows[0].status}}</b></div>
<div class='card'>Best Symbols<br><b>{{rows[0].best_symbols}}</b></div>
</div>
<h2>Strategy Factory Chart</h2>{{chart|safe}}
<h2>Leaderboard</h2>{{table|safe}}
""",rows=rows,chart=chart_html(),table=pd.DataFrame(rows).to_html(index=False))
    return page("V10.1 Strategy Factory",body)

@app.route("/leaderboard")
def leaderboard():
    return page("Leaderboard","<h1>Autonomous Strategy Leaderboard</h1><p><a class='button' href='/'>Back</a></p>"+pd.DataFrame(strategy_factory()).to_html(index=False))

@app.route("/ideas")
def ideas():
    return page("AI Strategy Ideas","<h1>AI-Generated Strategy Ideas</h1><p><a class='button' href='/'>Back</a></p>"+pd.DataFrame(ai_generate_strategy_ideas()).to_html(index=False))

@app.route("/strategy/<name>")
def strategy_detail(name):
    return page("Strategy Detail",f"<h1>{name}</h1><p><a class='button' href='/'>Back</a></p>"+pd.DataFrame(all_strategy_results(name)).to_html(index=False))

@app.route("/report")
def report():
    return page("Strategy Report","<h1>Autonomous Strategy Factory Report</h1><p><a class='button' href='/'>Back</a> <a class='button' href='/download_report'>Download</a></p><pre>"+report_text()+"</pre>")

@app.route("/download_report")
def download_report():
    report_text()
    return send_file(REPORT,as_attachment=True)

@app.route("/download_leaderboard")
def download_leaderboard():
    strategy_factory()
    return send_file(LEADERBOARD,as_attachment=True)

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    print(f"Starting NSE Signal Bot on port {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )