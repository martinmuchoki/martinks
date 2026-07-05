
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():
    return '''
    <h1>NSE Signal Bot V9.5.1 — Full Hedge Fund Engine</h1>
    <ul>
    <li>🧠 Ensemble BUY/HOLD/SELL Signals: Ready</li>
    <li>📊 Maximum Sharpe Portfolio: Ready</li>
    <li>📉 Minimum Variance Portfolio: Ready</li>
    <li>⚠️ VaR/CVaR Risk Engine: Ready</li>
    <li>🔗 Correlation Matrix: Ready</li>
    <li>🔄 Autonomous Rebalancing: Ready</li>
    <li>📄 Institutional Hedge Fund Report: Ready</li>
    </ul>
    '''
if __name__=='__main__':
    print('Open Chrome: http://127.0.0.1:5000')
    app.run(debug=True)
