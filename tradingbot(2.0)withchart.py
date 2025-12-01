import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------
# Data Handling
# -------------------------
class DataHandler:
    def __init__(self, ticker, start, end):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.data = None

    def load_data(self):
        data = yf.download(self.ticker, start=self.start, end=self.end)
        data = data[["Close"]]

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]  # Flatten multiindex if present

        data.dropna(inplace=True)
        self.data = data 
        return data 

# -------------------------
# Strategy
# -------------------------
class Strategy:
    def __init__(self, data, sma, lma):
        self.data = data 
        self.sma_window = sma 
        self.lma_window = lma 

    def apply_indicators(self):
        ds = self.data.copy()
        ds["SMA"] = ds["Close"].rolling(window=self.sma_window).mean()
        ds["LMA"] = ds["Close"].rolling(window=self.lma_window).mean()
        return ds

    def generate_signals(self):
        ds = self.apply_indicators().dropna().copy()

        ds["signal"] = 0
        ds.loc[ds["SMA"] > ds["LMA"], "signal"] = 1
        ds.loc[ds["SMA"] < ds["LMA"], "signal"] = -1
        ds["signal_change"] = ds["signal"].diff()

        ds["trade"] = ""
        ds.loc[(ds["SMA"] > ds["LMA"]) & (ds["SMA"].shift(1) <= ds["LMA"].shift(1)), "trade"] = "buy"
        ds.loc[(ds["SMA"] < ds["LMA"]) & (ds["SMA"].shift(1) >= ds["LMA"].shift(1)), "trade"] = "sell"

        ds["trade"] = ds["trade"].fillna("").astype(str).str.strip()
        return ds

# -------------------------
# Backtester
# -------------------------
class Backtester:
    def __init__(self, data, initial_balance=500):
        self.data = data
        self.balance = initial_balance
        self.position = 0
        self.entry_price = None
        self.shares = 0
        self.trade_history = []

    def run(self):
        ds = self.data

        for date, row in ds.iterrows():
            trade = str(row["trade"]).strip().lower()

            if trade == "buy" and self.position == 0:
                self.shares = self.balance // row["Close"]
                self.entry_price = row["Close"]
                self.balance -= self.shares * row["Close"]
                self.position = 1
                self.trade_history.append((date, "BUY", self.entry_price, self.shares))

            elif trade == "sell" and self.position == 1:
                exit_price = row["Close"]
                self.balance += self.shares * exit_price
                self.trade_history.append((date, "SELL", exit_price, self.shares))
                self.position = 0
                self.shares = 0
                self.entry_price = None

        # Final sell if holding at end
        if self.position == 1:
            exit_price = ds["Close"].iloc[-1]
            self.balance += self.shares * exit_price
            self.trade_history.append((ds.index[-1], "SELL", exit_price, self.shares))
            self.position = 0
            self.shares = 0
            self.entry_price = None

        return self.balance, self.trade_history

# -------------------------
# Trader
# -------------------------
class Trader:
    def __init__(self, ticker, start, end, sma, lma):
        self.data_handler = DataHandler(ticker, start, end)
        self.data = self.data_handler.load_data()

        self.strat = Strategy(self.data, sma, lma)
        self.moving_averages = self.strat.apply_indicators()
        self.data = self.strat.generate_signals()

        if isinstance(self.data.index, pd.MultiIndex):
            self.data = self.data.reset_index(level=0)
       
        self.backtester = Backtester(self.data)  

    def execute(self):
        final_balance, history = self.backtester.run()

        print(self.data[self.data['trade'] != ''][['Close','SMA','LMA','trade']].tail(50))  
        print("\n==============================")
        print("FINAL BACKTEST RESULTS")
        print("==============================")
        print("Final Balance:", final_balance)
        print("\nTrades:")
        for i in history:
            print(i)

        # Plot trading signals
        self.plot_trades()

    def plot_trades(self):
        plt.figure(figsize=(14,7))
        plt.plot(self.data['Close'], label='Close Price', color='blue', alpha=0.6)
        plt.plot(self.data['SMA'], label=f'SMA ({self.strat.sma_window})', color='orange')
        plt.plot(self.data['LMA'], label=f'LMA ({self.strat.lma_window})', color='green')

        buys = self.data[self.data['trade'] == 'buy']
        sells = self.data[self.data['trade'] == 'sell']

        plt.scatter(buys.index, buys['Close'], marker='^', color='g', s=100, label='Buy Signal')
        plt.scatter(sells.index, sells['Close'], marker='v', color='r', s=100, label='Sell Signal')

        plt.title(f"{self.data_handler.ticker} Trading Signals")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True)
        plt.show()

# -------------------------
# Main
# -------------------------
def main():
    bot = Trader(
        ticker="GOOG",
        start="2023-01-01",
        end="2025-12-01",
        sma=10,
        lma=50
    )
    bot.execute()

if __name__ == "__main__":
    main()
