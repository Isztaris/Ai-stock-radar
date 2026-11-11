# AI Stock Radar – prototyp

Skaner akcji USA dla transakcji 1–5 sesji. Benchmark: **4,5% rocznie brutto** (lokata), czyli 3,645% netto po 19% podatku.

## Uruchomienie
1. Zainstaluj Python 3.10+.
2. W terminalu przejdź do folderu projektu.
3. `python -m pip install -r requirements.txt`
4. `streamlit run app.py`

Panel otworzy się w przeglądarce (zwykle http://localhost:8501).

## Co działa
- Pobiera ostatni rok dziennych notowań z Yahoo Finance (przez `yfinance`).
- Analizuje EMA20/50, RSI, MACD, wolumen i pięciodniowe momentum.
- Wystawia mechaniczne sygnały KUP / CZEKAJ / SPRZEDAJ-UNIKAJ.
- Wylicza orientacyjny stop-loss (1,5 ATR) i cel (3 ATR).
- Uruchamia uproszczony backtest: sygnał po zamknięciu dnia, zakup po otwarciu następnego dnia, wyjście do 5 sesji, koszty i luki cenowe.
- Pozwala eksportować CSV oraz oszacować wielkość pozycji.

## Ograniczenia
To **prototyp regułowy, a nie wytrenowany model AI**. Nie posiada połączenia z rachunkiem maklerskim, automatycznych zleceń ani ciągłego monitoringu. Dane mogą być opóźnione lub niekompletne. Dostęp do danych i ich wykorzystanie zależą od warunków dostawcy. Wyniki backtestu mogą być nadmiernie dopasowane; nie ma gwarancji pobicia lokaty. Kalkulacja benchmarku i podatku jest uproszczona. Wykorzystanie realnych pieniędzy wymaga dalszej walidacji, testów poza próbą i kontroli ryzyka.
