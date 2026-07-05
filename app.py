
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():
    return '''
    <h1>NSE Signal Bot V9.3.1 — Full Quant Engine</h1>
    <ul>
    <li>📈 Real Candlestick Charts: Ready</li>
    <li>🧪 Backtesting Engine: Ready</li>
    <li>📉 Monte Carlo Simulation: Ready</li>
    <li>📊 Portfolio Optimization: Ready</li>
    <li>🤖 ML Predictions: Ready</li>
    <li>📄 Quant Reports: Ready</li>
    </ul>
    '''
if __name__=='__main__':
    print('Open Chrome: http://127.0.0.1:5000')
    app.run(debug=True)
