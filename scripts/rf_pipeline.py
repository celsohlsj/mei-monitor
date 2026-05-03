#!/usr/bin/env python3
"""
Prophet Fire Forecast Pipeline — YbYrá-BR
==========================================
MEI (SARIMA, mei_data.json) + AMO (SARIMA) + PDO (SARIMA) + INPE
→ Facebook Prophet → prophet_forecast.json

Features como regressores: MEI_lag1, AMO_lag1, PDO_lag1
Target  : focos mensais Amazônia — INPE BDQueimadas (log1p)
Índices : previsão via SARIMA Sazonal (s=12) para alimentar o Prophet

Usage:
    python scripts/rf_pipeline.py            # full run
    python scripts/rf_pipeline.py --dry-run  # usa dados embutidos (sem fetch)
    python scripts/rf_pipeline.py --steps 12
"""

import sys, json, argparse, warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet
from sklearn.metrics import mean_absolute_error

warnings.filterwarnings("ignore")

ROOT     = Path(__file__).parent.parent
DOCS     = ROOT / "docs"
MEI_JSON = DOCS / "mei_data.json"
RF_JSON  = DOCS / "rf_forecast.json"

BISEASONS = ["DJ","JF","FM","MA","AM","MJ","JJ","JA","AS","SO","ON","ND"]
REGRESSORS = ["mei_lag1", "amo_lag1", "pdo_lag1"]

AMO_URL  = "https://psl.noaa.gov/data/correlation/amon.us.long.data"
PDO_URL  = "https://psl.noaa.gov/data/correlation/pdo.data"
INPE_URL = ("https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/"
            "media/bioma/csv_estatisticas/historico_bioma_amazonia.csv")

INPE_FALLBACK = """,Janeiro,Fevereiro,Março,Abril,Maio,Junho,Julho,Agosto,Setembro,Outubro,Novembro,Dezembro,Total
1998,,,,,,1549.0,3192.0,20075.0,19214.0,8777.0,3833.0,2547.0,59187.0
1999,160.0,358.0,130.0,70.0,449.0,1439.0,3675.0,21525.0,16106.0,12794.0,4449.0,1703.0,62858.0
2000,87.0,182.0,405.0,92.0,930.0,3211.0,1510.0,12791.0,10062.0,10226.0,5497.0,3175.0,48168.0
2001,165.0,699.0,1134.0,617.0,916.0,4227.0,1816.0,17679.0,15528.0,14292.0,8346.0,4256.0,69675.0
2002,590.0,667.0,901.0,405.0,1490.0,5702.0,7529.0,43484.0,48549.0,27110.0,23660.0,9174.0,169261.0
2003,3704.0,1573.0,1997.0,1038.0,1983.0,6848.0,15918.0,34765.0,47789.0,25341.0,19631.0,13813.0,174400.0
2004,2178.0,805.0,1035.0,1012.0,3131.0,9179.0,19179.0,43320.0,71522.0,23928.0,26424.0,16924.0,218637.0
2005,4314.0,1048.0,758.0,832.0,1746.0,2954.0,19364.0,63764.0,68560.0,26624.0,16790.0,6966.0,213720.0
2006,1973.0,879.0,903.0,709.0,843.0,2522.0,6995.0,34208.0,51028.0,18309.0,17474.0,8579.0,144422.0
2007,1918.0,1761.0,1431.0,760.0,1176.0,3519.0,6196.0,46385.0,73141.0,28731.0,16025.0,5437.0,186480.0
2008,938.0,527.0,860.0,569.0,383.0,1248.0,5901.0,21445.0,26469.0,23518.0,15450.0,6145.0,103453.0
2009,1095.0,354.0,584.0,435.0,673.0,1023.0,2327.0,9732.0,20527.0,19323.0,19104.0,6505.0,81682.0
2010,1697.0,1147.0,1176.0,633.0,1026.0,1911.0,5868.0,45018.0,43933.0,14798.0,12167.0,5240.0,134614.0
2011,771.0,271.0,427.0,465.0,528.0,1083.0,2445.0,8002.0,16987.0,9760.0,9815.0,7632.0,58186.0
2012,1203.0,438.0,484.0,473.0,855.0,1875.0,3095.0,20687.0,24067.0,14814.0,13259.0,5469.0,86719.0
2013,1181.0,374.0,738.0,518.0,796.0,1450.0,2531.0,9444.0,16786.0,10242.0,6615.0,8013.0,58688.0
2014,1573.0,473.0,1010.0,632.0,673.0,1628.0,2766.0,20113.0,20522.0,13221.0,12169.0,7773.0,82553.0
2015,2042.0,1047.0,572.0,762.0,407.0,1287.0,2817.0,20471.0,29326.0,19469.0,16935.0,11303.0,106438.0
2016,4657.0,1559.0,2024.0,1075.0,895.0,1663.0,6120.0,18340.0,20460.0,14234.0,11610.0,5124.0,87761.0
2017,796.0,379.0,736.0,618.0,805.0,1759.0,7986.0,21244.0,36569.0,14457.0,14105.0,7985.0,107439.0
2018,1444.0,888.0,1359.0,513.0,772.0,1980.0,4788.0,10421.0,24803.0,10654.0,8881.0,1842.0,68345.0
2019,1419.0,1368.0,3383.0,1702.0,854.0,1880.0,5318.0,30900.0,19925.0,7855.0,11297.0,3275.0,89176.0
2020,1200.0,1196.0,1641.0,789.0,829.0,2248.0,6803.0,29307.0,32017.0,17326.0,6321.0,3484.0,103161.0
2021,794.0,864.0,643.0,615.0,1166.0,2305.0,4977.0,28060.0,16742.0,11549.0,5779.0,1596.0,75090.0
2022,1226.0,584.0,490.0,384.0,2287.0,2562.0,5373.0,33116.0,41282.0,13911.0,11062.0,2756.0,115033.0
2023,1056.0,734.0,1019.0,768.0,1692.0,3075.0,5772.0,17372.0,26449.0,22061.0,13940.0,4701.0,98639.0
2024,2049.0,3157.0,2654.0,1117.0,1670.0,2842.0,11434.0,38266.0,41463.0,16169.0,14158.0,5367.0,140346.0
2025,1219.0,399.0,772.0,293.0,836.0,1650.0,2183.0,6094.0,7211.0,7868.0,9568.0,5038.0,43131.0
2026,2056.0,873.0,873.0,402.0,,,,,,,,,4204.0"""


# ── helpers ────────────────────────────────────────────────────────────────────

def _get(url, timeout=25):
    hdrs = {"User-Agent": "MEI-Monitor/2.0 (IPAM/UFMA; celsohlsj@gmail.com)"}
    proxies = [
        f"https://api.allorigins.win/raw?url={requests.utils.quote(url)}",
        f"https://corsproxy.io/?url={requests.utils.quote(url)}",
    ]
    for u in [url] + proxies:
        try:
            r = requests.get(u, timeout=timeout, headers=hdrs)
            r.raise_for_status()
            if len(r.text) > 300:
                return r.text
        except Exception as e:
            print(f"    ⚠ {u[:70]}: {e}")
    return None


# ── 1. Load MEI ────────────────────────────────────────────────────────────────

def load_mei():
    """Lê observações + previsões SARIMA de mei_data.json."""
    data = json.loads(MEI_JSON.read_text())
    rows = []
    for o in data["observations"]:
        month = BISEASONS.index(o["season"]) + 1
        rows.append({"year": int(o["year"]), "month": month, "mei": float(o["mei"])})
    df = pd.DataFrame(rows).sort_values(["year","month"]).reset_index(drop=True)
    sarima_fc = data.get("forecasts", [])
    last = data["statistics"]["year_max"]
    model_type = data.get("model", {}).get("type", "SARIMA")
    print(f"  ✓ MEI: {len(df)} registros  (até {last})  [{model_type}]")
    return df, sarima_fc


# ── 2. Fetch AMO / PDO ─────────────────────────────────────────────────────────

def _parse_monthly(text, key):
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s or not s[:4].isdigit():
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        year = int(parts[0])
        for m in range(12):
            try:
                v = float(parts[m + 1])
            except (IndexError, ValueError):
                continue
            if abs(v) > 90 or v <= -99:
                continue
            rows.append({"year": year, "month": m + 1, key: round(v, 4)})
    return pd.DataFrame(rows).sort_values(["year","month"]).reset_index(drop=True)


def fetch_amo(dry_run=False):
    if not dry_run:
        text = _get(AMO_URL)
        if text:
            df = _parse_monthly(text, "amo")
            if len(df) > 100:
                print(f"  ✓ AMO: {len(df)} meses")
                return df
    print("  ⚠ AMO indisponível — usando climatologia zero")
    return pd.DataFrame(columns=["year","month","amo"])


def fetch_pdo(dry_run=False):
    if not dry_run:
        text = _get(PDO_URL)
        if text:
            df = _parse_monthly(text, "pdo")
            if len(df) > 100:
                print(f"  ✓ PDO: {len(df)} meses")
                return df
    print("  ⚠ PDO indisponível — usando climatologia zero")
    return pd.DataFrame(columns=["year","month","pdo"])


# ── 3. INPE fire data ──────────────────────────────────────────────────────────

def _parse_inpe(csv_text):
    rows = []
    for line in csv_text.strip().splitlines():
        parts = line.split(",")
        try:
            year = int(parts[0].strip())
        except ValueError:
            continue
        for m in range(12):
            try:
                vs = parts[m + 1].strip()
                if not vs:
                    continue
                v = float(vs)
                if v >= 0:
                    rows.append({"year": year, "month": m + 1, "focos": int(round(v))})
            except (IndexError, ValueError):
                pass
    return pd.DataFrame(rows).sort_values(["year","month"]).reset_index(drop=True)


def load_inpe(dry_run=False):
    if not dry_run:
        text = _get(INPE_URL, timeout=30)
        if text and len(text.splitlines()) > 10:
            df = _parse_inpe(text)
            if len(df) > 100:
                print(f"  ✓ INPE: {len(df)} meses  ({df['year'].min()}–{df['year'].max()})")
                return df
    df = _parse_inpe(INPE_FALLBACK)
    print(f"  ✓ INPE (embutido): {len(df)} meses")
    return df


# ── 4. Merge + lag regressors ──────────────────────────────────────────────────

def build_dataset(mei_df, amo_df, pdo_df, fire_df):
    """
    Mescla MEI + AMO + PDO + INPE e cria regressores com lag-1.
    Retorna DataFrame pronto para o Prophet.
    """
    empty_amo = pd.DataFrame({"year": [], "month": [], "amo": []})
    empty_pdo = pd.DataFrame({"year": [], "month": [], "pdo": []})

    df = (fire_df
          .merge(mei_df[["year","month","mei"]], on=["year","month"], how="left")
          .merge(amo_df if len(amo_df) else empty_amo,
                 on=["year","month"], how="left")
          .merge(pdo_df if len(pdo_df) else empty_pdo,
                 on=["year","month"], how="left")
          .sort_values(["year","month"])
          .reset_index(drop=True))

    for col in ["amo", "pdo"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(df[col].expanding().mean()).fillna(0.0)
    df["mei"] = df["mei"].fillna(df["mei"].expanding().mean()).fillna(0.0)

    # Lag-1: valor do mês anterior como preditor do mês atual
    df["mei_lag1"] = df["mei"].shift(1)
    df["amo_lag1"] = df["amo"].shift(1)
    df["pdo_lag1"] = df["pdo"].shift(1)

    # Coluna de data para Prophet
    df["ds"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    df["y"]  = np.log1p(df["focos"].astype(float))

    df = df.dropna(subset=REGRESSORS).reset_index(drop=True)

    y0, m0 = int(df.iloc[0]["year"]),  int(df.iloc[0]["month"])
    y1, m1 = int(df.iloc[-1]["year"]), int(df.iloc[-1]["month"])
    print(f"  ✓ Dataset Prophet: {len(df)} linhas  ({y0}-{m0:02d} → {y1}-{m1:02d})")
    return df


# ── 5. SARIMA para previsão dos índices oceânicos ──────────────────────────────

def _sarima_forecast_series(series_vals, periods, name=""):
    """
    Ajusta o melhor SARIMA(p,d,q)(P,D,Q,12) por AIC e retorna
    (valores_previstos, order, seasonal_order).
    """
    clean = np.array(series_vals, dtype=float)
    clean = clean[~np.isnan(clean)]

    if len(clean) < 24:
        print(f"  ⚠ {name}: série curta ({len(clean)}) — usando média")
        mu = float(np.nanmean(clean)) if len(clean) else 0.0
        return np.full(periods, mu), None, None

    candidates = [
        ((0, 1, 1), (0, 1, 1, 12)),
        ((1, 1, 1), (0, 1, 1, 12)),
        ((1, 1, 0), (0, 1, 1, 12)),
        ((0, 1, 1), (1, 1, 0, 12)),
        ((1, 1, 1), (1, 1, 0, 12)),
    ]

    best_aic = np.inf
    best_res = None
    best_ord = (None, None)

    for order, sorder in candidates:
        try:
            mod = SARIMAX(
                clean,
                order=order,
                seasonal_order=sorder,
                enforce_stationarity=False,
                enforce_invertibility=False,
                simple_differencing=True,
            )
            res = mod.fit(disp=False, maxiter=400)
            aic = float(res.aic)
            if not np.isnan(aic) and not np.isinf(aic) and aic < best_aic:
                best_aic = aic
                best_res = res
                best_ord = (order, sorder)
        except Exception:
            continue

    if best_res is None:
        print(f"  ⚠ {name}: SARIMA falhou — usando média")
        return np.full(periods, float(np.mean(clean))), None, None

    fc    = best_res.get_forecast(steps=periods)
    vals  = fc.predicted_mean.values
    o, so = best_ord
    print(f"  ✓ {name} SARIMA({o[0]},{o[1]},{o[2]})({so[0]},{so[1]},{so[2]},12) "
          f"AIC={round(best_aic, 1)}")
    return vals, list(o), list(so)


# ── 6. Treinar e prever com Prophet ───────────────────────────────────────────

def _make_prophet():
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        interval_width=0.90,
        uncertainty_samples=500,
    )
    for col in REGRESSORS:
        m.add_regressor(col)
    return m


def train_and_forecast(df_full, future_reg_df, steps):
    """
    Treina Prophet, calcula métricas no conjunto de teste (últimos ~20%)
    e retorna previsões para os próximos `steps` meses.
    """
    n     = len(df_full)
    split = max(int(n * 0.8), n - 36)

    df_tr = df_full.iloc[:split].copy()
    df_te = df_full.iloc[split:].copy()

    train_cols = ["ds", "y"] + REGRESSORS

    # ── Validação
    m_val = _make_prophet()
    m_val.fit(df_tr[train_cols])

    pred_tr = m_val.predict(df_tr[["ds"] + REGRESSORS])
    pred_te = m_val.predict(df_te[["ds"] + REGRESSORS])

    def mape(y_true_log, y_pred_log):
        yt = np.maximum(np.expm1(y_true_log), 1.0)
        yp = np.maximum(np.expm1(y_pred_log), 0.0)
        return float(np.mean(np.abs((yt - yp) / yt)) * 100)

    mape_tr = round(mape(df_tr["y"].values, pred_tr["yhat"].values), 2)
    mape_te = round(mape(df_te["y"].values, pred_te["yhat"].values), 2)
    mae_te  = round(float(mean_absolute_error(
                        np.expm1(df_te["y"].values),
                        np.maximum(np.expm1(pred_te["yhat"].values), 0))), 1)

    print(f"  ✓ Prophet (validação)  MAPE_treino={mape_tr}%  "
          f"MAPE_teste={mape_te}%  MAE_teste={mae_te:.0f}")

    # ── Retreinar em todos os dados
    m_full = _make_prophet()
    m_full.fit(df_full[train_cols])

    # ── Previsão futura
    future = m_full.make_future_dataframe(periods=steps, freq="MS",
                                          include_history=False)
    for col in REGRESSORS:
        future[col] = future_reg_df[col].values[:steps]

    fc = m_full.predict(future)

    forecasts = []
    for i, (_, row) in enumerate(fc.iterrows(), 1):
        pred = max(0, int(round(float(np.expm1(row["yhat"])))))
        lo   = max(0, int(round(float(np.expm1(row["yhat_lower"])))))
        hi   = max(0, int(round(float(np.expm1(row["yhat_upper"])))))
        dt   = pd.Timestamp(row["ds"])
        forecasts.append({
            "year":       int(dt.year),
            "month":      int(dt.month),
            "step":       i,
            "focos_pred": pred,
            "lo":         lo,
            "hi":         hi,
        })
        print(f"  +{i:2d}  {dt.year}-{dt.month:02d}  focos≈{pred:>7,}  [{lo:,} – {hi:,}]")

    return mape_tr, mape_te, mae_te, forecasts, split


# ── 7. Construir dataframe de regressores futuros ──────────────────────────────

def build_future_regressors(df_full, sarima_mei_fc, amo_fc_vals, pdo_fc_vals, steps):
    """
    Para o Prophet prever o mês T+k, o regressor lag-1 precisa do valor em T+k-1.
    - lag-1 do mês T+1 = último valor observado (T)
    - lag-1 do mês T+k = previsão SARIMA do mês T+k-1  (para k >= 2)
    """
    last_mei = float(df_full["mei"].iloc[-1])
    last_amo = float(df_full["amo"].iloc[-1])
    last_pdo = float(df_full["pdo"].iloc[-1])

    # MEI futuro vem das previsões SARIMA de mei_data.json
    mei_vals = [float(f["mei"]) for f in sarima_mei_fc[:steps]]
    # Preenche com média caso insuficiente
    if len(mei_vals) < steps:
        mei_vals += [float(np.mean(mei_vals or [last_mei]))] * (steps - len(mei_vals))

    # Regressores lag-1: shift de 1 período para frente
    # índice 0 (mês T+1): usa o último observado
    # índice k (mês T+k+1): usa forecast do passo k
    mei_lag1 = [last_mei] + list(mei_vals[:steps - 1])
    amo_lag1 = [last_amo] + list(amo_fc_vals[:steps - 1])
    pdo_lag1 = [last_pdo] + list(pdo_fc_vals[:steps - 1])

    last_date  = df_full["ds"].max()
    fut_dates  = pd.date_range(start=last_date + pd.DateOffset(months=1),
                               periods=steps, freq="MS")
    return pd.DataFrame({
        "ds":       fut_dates,
        "mei_lag1": mei_lag1,
        "amo_lag1": amo_lag1,
        "pdo_lag1": pdo_lag1,
    })


# ── 8. Export ──────────────────────────────────────────────────────────────────

def export_json(mei_df, amo_df, pdo_df, fire_df,
                prophet_meta, prophet_fc):
    # Série climática para o frontend (AFCI, visualizações)
    cl = (mei_df
          .merge(amo_df if len(amo_df) else
                 pd.DataFrame({"year":[],"month":[],"amo":[]}),
                 on=["year","month"], how="left")
          .merge(pdo_df if len(pdo_df) else
                 pd.DataFrame({"year":[],"month":[],"pdo":[]}),
                 on=["year","month"], how="left")
          .sort_values(["year","month"]).reset_index(drop=True))

    for col in ["amo","pdo"]:
        if col not in cl.columns:
            cl[col] = None
        cl[col] = cl[col].where(cl[col].notna(), other=None)

    def to_list(df):
        return [{k: (None if (isinstance(v, float) and np.isnan(v)) else
                     (int(v)   if isinstance(v, (np.integer,)) else
                      (float(round(v, 4)) if isinstance(v, float) else v)))
                 for k, v in row.items()}
                for row in df.to_dict("records")]

    payload = {
        "meta": {
            "updated_utc"  : datetime.now(timezone.utc).isoformat(),
            "pipeline"     : "YbYrá-BR Prophet Pipeline — IPAM/UFMA (CNPq 401741/2023-0)",
            "model_type"   : "Facebook Prophet + SARIMA (índices oceânicos)",
            "mei_records"  : len(mei_df),
            "fire_records" : len(fire_df),
            "amo_records"  : len(amo_df),
            "pdo_records"  : len(pdo_df),
        },
        "climate_series"  : to_list(cl[["year","month","mei","amo","pdo"]]),
        "fire_monthly"    : to_list(fire_df[["year","month","focos"]]),
        # chaves canonicas novas
        "prophet_model"   : prophet_meta,
        "prophet_forecast": prophet_fc,
        # aliases para compatibilidade com frontend antigo em cache
        "rf_model"        : prophet_meta,
        "rf_forecast"     : prophet_fc,
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    RF_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  ✓ {RF_JSON}  ({RF_JSON.stat().st_size/1024:.1f} KB)")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Pular fetches externos; usar dados embutidos")
    ap.add_argument("--steps", type=int, default=12,
                    help="Meses a prever (default 12)")
    args = ap.parse_args()

    print("\n══════════════════════════════════════════════════")
    print("  YbYrá-BR · Prophet Fire Forecast Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("══════════════════════════════════════════════════\n")

    print("[1/7] Carregando MEI (mei_data.json  ·  SARIMA)")
    mei_df, sarima_mei_fc = load_mei()

    print("\n[2/7] AMO")
    amo_df = fetch_amo(dry_run=args.dry_run)

    print("\n[3/7] PDO")
    pdo_df = fetch_pdo(dry_run=args.dry_run)

    print("\n[4/7] INPE BDQueimadas")
    fire_df = load_inpe(dry_run=args.dry_run)

    print("\n[5/7] Construindo dataset + regressores lag-1")
    df_full = build_dataset(mei_df, amo_df, pdo_df, fire_df)

    print(f"\n[6/7] SARIMA para AMO e PDO ({args.steps} meses)")
    amo_fc_vals, amo_order, amo_sorder = _sarima_forecast_series(
        df_full["amo"].values, args.steps, "AMO")
    pdo_fc_vals, pdo_order, pdo_sorder = _sarima_forecast_series(
        df_full["pdo"].values, args.steps, "PDO")

    future_reg_df = build_future_regressors(
        df_full, sarima_mei_fc, amo_fc_vals, pdo_fc_vals, args.steps)

    print(f"\n[7/7] Treinando Prophet e prevendo {args.steps} meses")
    mape_tr, mape_te, mae_te, prophet_fc, n_train = train_and_forecast(
        df_full, future_reg_df, args.steps)

    trained_on = (f"{int(df_full.iloc[0]['year'])}-{int(df_full.iloc[0]['month']):02d}"
                  f" a {int(df_full.iloc[-1]['year'])}-{int(df_full.iloc[-1]['month']):02d}")

    prophet_meta = {
        "model"            : "Facebook Prophet",
        "features"         : REGRESSORS,
        "seasonality_mode" : "multiplicative",
        "interval_width"   : 0.90,
        "n_samples"        : len(df_full),
        "n_train"          : n_train,
        "n_test"           : len(df_full) - n_train,
        "mape_train"       : mape_tr,
        "mape_test"        : mape_te,
        "mae_test"         : mae_te,
        "trained_on"       : trained_on,
        "sarima_mei"       : "ver mei_data.json",
        "sarima_amo"       : {"order": amo_order, "seasonal_order": amo_sorder},
        "sarima_pdo"       : {"order": pdo_order, "seasonal_order": pdo_sorder},
        # aliases para compatibilidade
        "r2_train"         : None,
        "r2_test"          : None,
        "lags"             : 1,
        "n_estimators"     : None,
    }

    print("\n[8/8] Exportando rf_forecast.json")
    export_json(mei_df, amo_df, pdo_df, fire_df, prophet_meta, prophet_fc)

    print("\n✓ Concluído.\n")


if __name__ == "__main__":
    main()
