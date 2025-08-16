import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Portfolio • Viz + Insight", page_icon="me.jpeg", layout="wide")
alt.data_transformers.disable_max_rows()

# ---------- Utils ----------
def detect_date_col(df):
    cands = [c for c in df.columns if any(k in c.lower() for k in ["date","tanggal","time","dt"])]
    for c in cands:
        s = pd.to_datetime(df[c], errors="coerce")
        if s.notna().mean() > 0.5:
            return c
    return None

def num_cols(df): return df.select_dtypes(include="number").columns.tolist()
def cat_cols(df): return [c for c in df.columns if df[c].dtype=="object" or "category" in str(df[c].dtype)]

def pct_change(a, b):
    if pd.isna(a) or pd.isna(b) or b==0: return np.nan
    return (a-b)/abs(b)*100

def knum(x):
    if pd.isna(x): return "—"
    if abs(x)>=1_000_000: return f"{x/1_000_000:.2f}M"
    if abs(x)>=1_000: return f"{x/1_000:.2f}K"
    return f"{x:.2f}"

# ---------- Sidebar ----------
st.sidebar.title("🧭 Navigasi")
page = st.sidebar.radio("", ["🏠 Beranda", "📊 Portfolio (Viz + Insight)", "📫 Kontak"])

# ---------- Beranda ----------
if page == "🏠 Beranda":
    col1, col2 = st.columns([1,2], gap="large")
    with col1:
        st.image("/content/me.jpeg", width=360)
    with col2:
        st.title("Hi, I'm Elqory 👋")
        st.write("""
        **Data Analyst / Aspiring Data Scientist**  
        Fokus di analisis data, model simpel yang ngasih jawaban cepat, dan dashboard yang enak dilihat.
        """)
        st.write("**Kontak:** elqoryc@gmail.com · [LinkedIn](https://www.linkedin.com/in/elqory-ceasardy/) · [GitHub]( ElqoryCeasardy/portofolio-streamlit)")
        st.caption(f"Last updated: {datetime.now().strftime('%d %b %Y')}")

# ---------- Portfolio ----------
elif page == "📊 Portfolio (Viz + Insight)":
    st.title("Projects & Visualisasi Interaktif")

    st.subheader("1) Pilih Dataset")
    up = st.file_uploader("Upload CSV (≤ 200MB)", type=["csv"])
    if up is not None:
        df = pd.read_csv(up)
        st.success("CSV berhasil dimuat.")
    else:
        np.random.seed(42)
        df = pd.DataFrame({
            "tanggal": pd.date_range("2024-01-01", periods=365, freq="D"),
            "penjualan": np.random.randint(100, 800, 365),
            "profit": np.random.randint(10, 200, 365),
            "channel": np.random.choice(["Online","Offline","Marketplace"], 365, p=[0.5,0.3,0.2])
        })
        st.info("Belum upload → lagi demo pakai dataset dummy (penjualan harian).")

    st.subheader("2) Preview Data")
    st.dataframe(df.head(20), use_container_width=True)

    dcol = detect_date_col(df)
    ncols = num_cols(df)
    ccols = cat_cols(df)

    st.markdown("---")
    st.subheader("3) Visualisasi & Insight")

    time_mode = st.toggle("Time-series mode (pakai kolom tanggal)", value=(dcol is not None))

    if time_mode:
        # ---------- Time series ----------
        if dcol is None:
            st.warning("Gak ketemu kolom tanggal otomatis. Pilih manual di bawah.")
        date_col = st.selectbox("Kolom tanggal", df.columns, index=(list(df.columns).index(dcol) if dcol in df.columns else 0))
        dfx = df.copy()
        dfx[date_col] = pd.to_datetime(dfx[date_col], errors="coerce")
        dfx = dfx.dropna(subset=[date_col])
        if not ncols:
            st.error("Gak ada kolom numerik.")
        else:
            y = st.selectbox("Metric (numerik)", ncols, index=(ncols.index("penjualan") if "penjualan" in ncols else 0))
            freq = st.selectbox("Agregasi waktu", ["D - Harian","W - Mingguan","M - Bulanan","Q - Kuartal"], index=2)
            agg = st.selectbox("Fungsi agregasi", ["sum","mean","median"], index=0)
            smooth = st.slider("Moving Average (opsional)", 1, 30, 1)

            code = freq.split(" - ")[0]
            grp = dfx.set_index(date_col).sort_index().resample(code)[y]
            if   agg=="sum":   series = grp.sum()
            elif agg=="mean":  series = grp.mean()
            else:              series = grp.median()
            series = series.to_frame(name=y)
            if smooth>1: series["MA"] = series[y].rolling(smooth, min_periods=1).mean()
            series = series.reset_index().rename(columns={series.columns[0]:"waktu"})

            # KPIs
            c1,c2,c3,c4 = st.columns(4)
            latest = series[y].iloc[-1] if len(series) else np.nan
            prev   = series[y].iloc[-2] if len(series)>1 else np.nan
            delta  = pct_change(latest, prev)
            peak_i = series[y].idxmax() if len(series) else None
            low_i  = series[y].idxmin() if len(series) else None
            c1.metric(f"{agg.upper()} {y} (terakhir)", knum(float(latest)), f"{delta:+.1f}% vs prev" if pd.notna(delta) else "—")
            if peak_i is not None: c2.metric("Puncak",  knum(float(series[y].iloc[peak_i])), series["waktu"].iloc[peak_i].date().isoformat())
            if low_i  is not None: c3.metric("Terendah",knum(float(series[y].iloc[low_i ])), series["waktu"].iloc[low_i ].date().isoformat())
            c4.metric("Volatilitas (std)", knum(float(series[y].std())))

            base = alt.Chart(series).encode(x=alt.X("waktu:T", title="Waktu"))
            main = base.mark_line(point=True).encode(y=alt.Y(f"{y}:Q", title=f"{agg} {y}"),
                                                    tooltip=[alt.Tooltip("waktu:T"), alt.Tooltip(f"{y}:Q")])
            if "MA" in series.columns:
                ma = base.mark_line(strokeDash=[6,4]).encode(y="MA:Q", tooltip=[alt.Tooltip("waktu:T"), alt.Tooltip("MA:Q")])
                ch = (main + ma).interactive()
            else:
                ch = main.interactive()
            st.altair_chart(ch, use_container_width=True)

            # Insight otomatis
            try:
                idx = np.arange(len(series))
                slope = np.polyfit(idx, series[y].values, 1)[0]
                trend = "naik" if slope>0 else "turun" if slope<0 else "flat"
                pchg  = pct_change(series[y].iloc[-1], series[y].iloc[0])
                peak_t = series["waktu"].iloc[series[y].idxmax()].strftime("%b %Y")
                low_t  = series["waktu"].iloc[series[y].idxmin()].strftime("%b %Y")
                st.markdown(f"""
                **Insight cepat:**  
                • Tren **{y}** cenderung **{trend}** (total perubahan ~ **{pchg:+.1f}%**).  
                • Puncak di **{peak_t}**, terendah di **{low_t}**.  
                • Kalau masih noisy, naikin **Moving Average**.
                """)
            except:
                st.caption("Insight otomatis gak kebaca (data terlalu pendek?).")

    else:
        # ---------- Non time series ----------
        chart_type = st.selectbox("Tipe chart", ["Histogram","Boxplot","Bar by Category","Scatter"])
        nnow = num_cols(df)
        if chart_type in ["Histogram","Boxplot"]:
            if not nnow: st.error("Butuh kolom numerik."); st.stop()
            y = st.selectbox("Kolom numerik", nnow)
            if chart_type=="Histogram":
                bins = st.slider("Jumlah bin", 10, 80, 40)
                ch = alt.Chart(df).mark_bar().encode(
                    x=alt.X(f"{y}:Q", bin=alt.Bin(maxbins=bins), title=y),
                    y="count()", tooltip=[alt.Tooltip(f"{y}:Q", bin=True), alt.Tooltip("count():Q")]
                ).interactive()
                st.altair_chart(ch, use_container_width=True)
                q1,q3 = np.nanpercentile(df[y], [25,75]); iqr=q3-q1
                out_pct = ((df[y] < q1-1.5*iqr) | (df[y] > q3+1.5*iqr)).mean()*100
                st.markdown(f"**Insight:** mean **{df[y].mean():.2f}**, median **{df[y].median():.2f}**, perkiraan outlier **{out_pct:.1f}%**.")
            else:
                cats = ["(tanpa)"] + cat_cols(df)
                by = st.selectbox("Kelompokkan (opsional)", cats)
                if by=="(tanpa)":
                    ch = alt.Chart(df).mark_boxplot().encode(y=f"{y}:Q")
                else:
                    ch = alt.Chart(df).mark_boxplot().encode(x=by, y=f"{y}:Q", tooltip=[by, y])
                st.altair_chart(ch, use_container_width=True)
                st.caption("Lihat median & IQR per kategori buat bandingin sebaran.")

        elif chart_type=="Bar by Category":
            cats = cat_cols(df)
            if not cats: st.error("Butuh kolom kategori."); st.stop()
            cat = st.selectbox("Kolom kategori", cats)
            if not nnow: st.error("Butuh kolom numerik."); st.stop()
            y = st.selectbox("Kolom numerik", nnow)
            agg = st.selectbox("Agregasi", ["sum","mean","median"], index=0)
            if   agg=="sum":   gp = df.groupby(cat, dropna=False)[y].sum()
            elif agg=="mean":  gp = df.groupby(cat, dropna=False)[y].mean()
            else:              gp = df.groupby(cat, dropna=False)[y].median()
            gp = gp.reset_index().sort_values(y, ascending=False)
            topn = st.slider("Top-N", 3, min(30,len(gp)), min(10,len(gp)))
            show = gp.head(topn)
            ch = alt.Chart(show).mark_bar().encode(
                x=alt.X(f"{y}:Q", title=f"{agg} {y}"),
                y=alt.Y(f"{cat}:N", sort="-x"),
                tooltip=[cat, y]
            )
            st.altair_chart(ch, use_container_width=True)
            share = show[y].iloc[0]/gp[y].sum()*100 if gp[y].sum()!=0 else np.nan
            st.markdown(f"**Insight:** kategori top = **{show[cat].iloc[0]}**, kontribusi ~ **{share:.1f}%** dari total.")

        else:  # Scatter
            if len(nnow) < 2: st.error("Butuh minimal 2 kolom numerik."); st.stop()
            x = st.selectbox("X", nnow, index=0)
            y = st.selectbox("Y", nnow, index=1)
            samp = st.slider("Downsample", 500, min(5000, len(df)), min(2000, len(df)))
            dplot = df[[x,y]].dropna().sample(n=min(samp, len(df.dropna())), random_state=42)
            ch = alt.Chart(dplot).mark_point(opacity=0.35, size=30).encode(x=f"{x}:Q", y=f"{y}:Q", tooltip=[x,y]).interactive()
            st.altair_chart(ch, use_container_width=True)
            corr = np.corrcoef(dplot[x], dplot[y])[0,1] if len(dplot)>2 else np.nan
            st.markdown(f"**Insight:** korelasi Pearson ≈ **{corr:.2f}**.")

# ---------- Kontak ----------
else:
    st.title("Kontak")
    with st.form("contact"):
        name = st.text_input("Nama")
        email = st.text_input("Email")
        msg = st.text_area("Pesan")
        ok = st.form_submit_button("Kirim (dummy)")
        if ok: st.success("Terkirim (simulasi).")
