import requests
import pandas as pd
from datetime import datetime, timedelta
import time


class CryptoScanner:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.lookback_days = 30
        self.max_rebound_percent = 50  # Maximum rebound percentage to consider

    def get_trading_pairs(self):
        """Fetch all USDT trading pairs from Binance"""
        response = requests.get(f"{self.base_url}/exchangeInfo")
        symbols = response.json()['symbols']
        return [s['symbol'] for s in symbols if s['status'] == 'TRADING' and s['quoteAsset'] == 'USDT']

    def get_historical_klines(self, symbol):
        """Fetch historical klines (candlestick data) for a symbol"""
        end_time = int(time.time() * 1000)
        start_time = end_time - (self.lookback_days * 24 * 60 * 60 * 1000)

        params = {
            'symbol': symbol,
            'interval': '1d',
            'startTime': start_time,
            'endTime': end_time,
            'limit': 1000
        }

        try:
            response = requests.get(f"{self.base_url}/klines", params=params)
            data = response.json()

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close',
                                             'volume', 'close_time', 'quote_volume', 'trades',
                                             'taker_buy_base', 'taker_buy_quote', 'ignored'])

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Convert price columns to float
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)

            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def analyze_price_action(self, symbol, df):
        """Analyze price action to find significant drops with limited rebounds"""
        if df is None or len(df) < 2:
            return None

        # Find highest price and its date
        high_price = df['high'].max()
        high_date = df.loc[df['high'] == high_price, 'timestamp'].iloc[0]

        # Find lowest price after the high
        low_df = df[df['timestamp'] > high_date]
        if len(low_df) == 0:
            return None

        low_price = low_df['low'].min()
        low_date = low_df.loc[low_df['low'] == low_price, 'timestamp'].iloc[0]

        # Calculate current price and rebound
        current_price = float(df['close'].iloc[-1])

        # Calculate percentages
        drop_percent = ((high_price - low_price) / high_price) * 100
        rebound_percent = ((current_price - low_price) / low_price) * 100

        # Only return if rebound is less than max_rebound_percent
        if rebound_percent < self.max_rebound_percent:
            return {
                'symbol': symbol,
                'high_date': high_date.strftime('%Y-%m-%d'),
                'high_price': high_price,
                'low_date': low_date.strftime('%Y-%m-%d'),
                'low_price': low_price,
                'drop_percent': drop_percent,
                'current_price': current_price,
                'rebound_percent': rebound_percent
            }
        return None

    def scan_market(self):
        """Scan the entire market for matching patterns"""
        results = []
        pairs = self.get_trading_pairs()

        print(f"Scanning {len(pairs)} trading pairs...")

        for i, symbol in enumerate(pairs):
            if i % 10 == 0:  # Progress update every 10 pairs
                print(f"Progress: {i}/{len(pairs)} pairs scanned")

            df = self.get_historical_klines(symbol)
            result = self.analyze_price_action(symbol, df)

            if result:
                results.append(result)

            time.sleep(0.1)  # Rate limiting

        # Convert results to DataFrame and sort by drop percentage
        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('drop_percent', ascending=False)
            return results_df
        return pd.DataFrame()


def main():
    scanner = CryptoScanner()
    results = scanner.scan_market()

    if not results.empty:
        print("\nFound patterns matching criteria:")
        print("\nTop dropping cryptocurrencies with limited rebounds:")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.float_format', lambda x: '%.4f' % x)
        print(results)
    else:
        print("No matching patterns found")


if __name__ == "__main__":
    main()