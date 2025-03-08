import yfinance as yf
import pandas as pd

class DataFetcher:
    def __init__(self):
        pass
    
    def fetch_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Fetch historical stock data from Yahoo Finance."""
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data