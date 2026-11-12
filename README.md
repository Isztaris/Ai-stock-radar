# AI Stock Radar 2.0 — wersja testowa

Pliki do GitHub: `app.py`, `requirements.txt`. Na Streamlit Community Cloud ustaw **Main file path: `app.py`**.

## Co nowego
- 26 spółek domyślnie, do 80 tickerów na skan.
- KUP wymaga trendu EMA20 > EMA50, ceny powyżej EMA20, dodatniego MACD i RSI 45–68 oraz wyniku >=75.
- SPRZEDAJ tylko po potwierdzeniu trendu spadkowego; CZEKAJ to odrębny stan.
- Backtest bez nakładających się pozycji, realizacja na następnej sesji.
- Portfel referencyjny: 1 AMZN kupiona za 269,50 USD.
- Benchmark lokaty 4,5% brutto rocznie.

To edukacyjny skaner techniczny, nie gwarantuje zysku. Ceny mogą być opóźnione. Skan nie obejmuje całego rynku USA, a testy na rzeczywistych danych nie zostały wykonane w tym środowisku.
