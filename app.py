import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="AI Stock Radar", page_icon="📈", layout="wide")
st.title("📈 AI Stock Radar")
st.caption("Skaner sygnałów swing trading (1–5 sesji). Dane Yahoo Finance mogą być opóźnione. Narzędzie edukacyjne, nie gwarantuje zysku.")
BENCHMARK = 0.045
DEFAULT = "PANW, AMD, NVDA, AVGO, MSFT, AAPL, GOOGL, META, AMZN, CRWD, FTNT, PLTR, MU, ANET, ORCL, QCOM, SMCI, TSLA, NFLX, NOW"

@st.cache_data(ttl=900, show_spinner=False)
def load_prices(ticker, period="1y"):
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=["Close"]).copy()

def indicators(df):
    d=df.copy()
    c=d["Close"]
    d["EMA20"]=c.ewm(span=20, adjust=False).mean()
    d["EMA50"]=c.ewm(span=50, adjust=False).mean()
    delta=c.diff()
    gain=delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs=gain/loss.replace(0,np.nan)
    d["RSI"]=100-100/(1+rs)
    ema12=c.ewm(span=12,adjust=False).mean()
    ema26=c.ewm(span=26,adjust=False).mean()
    d["MACD"]=ema12-ema26
    d["MACD_signal"]=d["MACD"].ewm(span=9,adjust=False).mean()
    d["VOL20"]=d["Volume"].rolling(20).mean()
    tr=pd.concat([(d["High"]-d["Low"]), (d["High"]-c.shift()).abs(), (d["Low"]-c.shift()).abs()],axis=1).max(axis=1)
    d["ATR14"]=tr.rolling(14).mean()
    d["ret5"]=c.pct_change(5)
    return d

def signal_at(d, i):
    if i<60: return None
    r=d.iloc[i]
    p=d.iloc[i-1]
    if not np.isfinite(r[["EMA20","EMA50","RSI","ATR14","VOL20"]].to_numpy(dtype=float)).all(): return None
    score=0
    score+=25 if r["Close"]>r["EMA20"] else 0
    score+=20 if r["EMA20"]>r["EMA50"] else 0
    score+=20 if r["MACD"]>r["MACD_signal"] else 0
    score+=15 if 45<=r["RSI"]<=68 else 0
    score+=10 if r["Volume"]>1.2*r["VOL20"] else 0
    score+=10 if 0<r["ret5"]<0.08 else 0
    # Avoid chasing excessive price extension and overbought readings.
    extended=(r["Close"]>1.08*r["EMA20"]) or (r["RSI"]>=75)
    buy=(score>=75 and not extended)
    sell=(r["Close"]<r["EMA20"] and r["MACD"]<r["MACD_signal"]) or r["RSI"]>=80
    action="KUP (sygnał)" if buy else "SPRZEDAJ / UNIKAJ" if sell else "CZEKAJ"
    entry=float(r["Close"])
    atr=float(r["ATR14"])
    stop=entry-1.5*atr
    target=entry+3.0*atr
    return {"score":score,"action":action,"close":entry,"rsi":float(r["RSI"]),
            "stop":stop,"target":target,"risk_pct":100*(entry-stop)/entry,
            "date":d.index[i].strftime("%Y-%m-%d"),"buy":buy}

def backtest(d, max_hold=5, commission_bps=10):
    # Uses previous day's close signal, executes at next day's OPEN.
    # No overlapping trades. Stop and target intraday; if both touched, assume STOP first.
    # Gaps through stop/target execute at OPEN. Otherwise exit at close after max_hold sessions.
    trades=[]
    i=61
    while i<len(d):
        s=signal_at(d,i-1)
        if not s or not s["buy"] or not np.isfinite(d["Open"].iloc[i]):
            i+=1
            continue
        entry=float(d["Open"].iloc[i])
        prev_atr=float(d["ATR14"].iloc[i-1])
        if not np.isfinite(prev_atr) or prev_atr<=0:
            i+=1;continue
        stop=entry-1.5*prev_atr
        target=entry+3*prev_atr
        exit_i=min(i+max_hold-1,len(d)-1)
        exit_price=float(d["Close"].iloc[exit_i])
        why="Limit czasu"
        for j in range(i,exit_i+1):
            op=float(d["Open"].iloc[j]); low=float(d["Low"].iloc[j]); high=float(d["High"].iloc[j])
            if op<=stop: exit_price=op;exit_i=j;why="Luka poniżej stop";break
            if op>=target: exit_price=op;exit_i=j;why="Luka powyżej celu";break
            if low<=stop: exit_price=stop;exit_i=j;why="Stop-loss";break
            if high>=target: exit_price=target;exit_i=j;why="Take-profit";break
        gross=exit_price/entry-1
        net=gross-2*commission_bps/10000
        trades.append({"Wejście":d.index[i].strftime("%Y-%m-%d"),
                       "Wyjście":d.index[exit_i].strftime("%Y-%m-%d"),
                       "Cena wejścia":entry,"Cena wyjścia":exit_price,
                       "Wynik brutto %":100*gross,"Wynik po kosztach %":100*net,
                       "Powód wyjścia":why})
        i=exit_i+1
    return pd.DataFrame(trades)

with st.sidebar:
    st.header("Ustawienia")
    raw=st.text_area("Tickery (USA)",DEFAULT,height=135)
    tickers=list(dict.fromkeys(t.strip().upper() for t in raw.replace("\n",",").split(",") if t.strip()))[:40]
    capital=st.number_input("Kapitał (PLN)",min_value=1000,value=20000,step=1000)
    risk=st.slider("Maks. ryzyko na transakcję (% kapitału)",0.1,2.0,0.5,0.1)
    commission=st.number_input("Łączny koszt w jedną stronę (punkty bazowe)",0,200,10,5,
        help="Przykładowe koszty: prowizja + spread + poślizg; 10 pb = 0,10%")
    st.metric("Benchmark lokaty (brutto / rok)","4,50%")
    st.metric("Benchmark po 19% podatku","3,645%")
    st.caption("Benchmark dzienny: 4,5% × liczba dni / 365 (uproszczenie).")

if st.button("🔎 Skanuj rynek",type="primary"):
    st.cache_data.clear()
st.subheader("Sygnały – wybrany koszyk")
rows=[]
frames={}
errors=[]
with st.spinner("Pobieranie i analiza danych..."):
    for t in tickers:
        try:
            d=load_prices(t)
            if len(d)<65:
                errors.append(t);continue
            d=indicators(d)
            s=signal_at(d,len(d)-1)
            if s:
                frames[t]=d
                risk_per_share=s["close"]-s["stop"]
                # Shares are USD-denominated; PLN capital needs an FX rate.
                rows.append({"Ticker":t,"Data sesji":s["date"],"Sygnał":s["action"],
                             "Ocena /100":s["score"],"Cena USD":round(s["close"],2),
                             "RSI":round(s["rsi"],1),"Stop USD":round(s["stop"],2),
                             "Cel USD":round(s["target"],2),
                             "Ryzyko do stop %":round(s["risk_pct"],2)})
        except Exception:
            errors.append(t)
if rows:
    result=pd.DataFrame(rows).sort_values(["Ocena /100","Ticker"],ascending=[False,True])
    st.dataframe(result,use_container_width=True,hide_index=True)
    st.caption("Sygnał opiera się na ostatniej dostępnej dziennej świecy, nie jest prognozą ceny. Stop może wykonać się gorzej przy luce.")
    st.download_button("⬇️ Pobierz sygnały CSV",result.to_csv(index=False).encode("utf-8-sig"),"sygnaly.csv","text/csv")
    ticker=st.selectbox("Szczegóły akcji",result["Ticker"].tolist())
    d=frames[ticker]
    s=signal_at(d,len(d)-1)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Sygnał",s["action"])
    c2.metric("Cena zamknięcia",f'{s["close"]:.2f} USD')
    c3.metric("Stop (modelowy)",f'{s["stop"]:.2f} USD')
    c4.metric("Cel (modelowy)",f'{s["target"]:.2f} USD')
    fig=go.Figure()
    fig.add_trace(go.Candlestick(x=d.index,open=d["Open"],high=d["High"],low=d["Low"],close=d["Close"],name="Cena"))
    fig.add_trace(go.Scatter(x=d.index,y=d["EMA20"],name="EMA20"))
    fig.add_trace(go.Scatter(x=d.index,y=d["EMA50"],name="EMA50"))
    fig.update_layout(height=480,xaxis_rangeslider_visible=False)
    st.plotly_chart(fig,use_container_width=True)
    st.subheader("Backtest – historyczna symulacja")
    bt=backtest(d,commission_bps=commission)
    if bt.empty:
        st.info("Brak historycznych transakcji spełniających warunki w dostępnej próbce.")
    else:
        win=(bt["Wynik po kosztach %"]>0).mean()*100
        avg=bt["Wynik po kosztach %"].mean()
        compounded=(np.prod(1+bt["Wynik po kosztach %"]/100)-1)*100
        a,b,c=st.columns(3)
        a.metric("Liczba transakcji",len(bt))
        b.metric("Skuteczność",f"{win:.1f}%")
        c.metric("Średnia na transakcję po kosztach",f"{avg:.2f}%")
        st.caption(f"Suma składana wyników transakcji: {compounded:.2f}% (hipotetyczna, nie jest stopą zwrotu portfela; nie uwzględnia dni bez pozycji).")
        st.dataframe(bt,use_container_width=True,hide_index=True)
        st.download_button("⬇️ Pobierz backtest CSV",bt.to_csv(index=False).encode("utf-8-sig"),f"backtest_{ticker}.csv","text/csv")
    st.subheader("Wielkość pozycji – kontrola ryzyka")
    fx=st.number_input("Kurs USD/PLN do kalkulacji (wpisz aktualny)",min_value=0.01,value=4.00,step=0.01)
    max_loss_pln=capital*risk/100
    risk_share_pln=max((s["close"]-s["stop"])*fx,0.01)
    qty=int(min(max_loss_pln/risk_share_pln,capital/(s["close"]*fx)))
    st.write(f"Limit planowanej straty: **{max_loss_pln:.2f} PLN**; maksymalnie **{qty} szt.** według modelowego stop-loss.")
    st.caption("To tylko kalkulacja pozycji: luka cenowa, brak płynności i koszty mogą zwiększyć stratę. USD/PLN nie jest pobierany automatycznie.")
else:
    st.warning("Nie uzyskano wystarczających danych dla podanych tickerów. Sprawdź połączenie z internetem.")
if errors:
    st.warning("Nie udało się przeanalizować: "+", ".join(errors))
st.divider()
st.markdown("""
**Jak czytać radar:** KUP oznacza spełnienie zestawu warunków technicznych, nie pewny zysk.
Backtest nie obejmuje podatków, kosztów przewalutowania (chyba że wpiszesz je w koszty), dywidend ani pełnej symulacji portfela.
Wyniki historyczne nie przewidują przyszłych. Przed realnymi transakcjami przetestuj strategię na danych poza próbą i na koncie demo.
""")
