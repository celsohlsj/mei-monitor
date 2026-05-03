#!/usr/bin/env python3
"""
MEI.v2 ENSO Pipeline
====================
Fetch → Validate → SARIMA Sazonal → Export JSON

Source : NOAA Physical Sciences Laboratory
URL    : https://psl.noaa.gov/enso/mei/data/meiv2.data
Format : bi-monthly (12 seasons/year: DJ JF FM MA AM MJ JJ JA AS SO ON ND)

Usage:
    python scripts/pipeline.py           # full run (fetch + model + export)
    python scripts/pipeline.py --dry-run # use cached data, skip fetch
    python scripts/pipeline.py --steps 12
"""

import sys, json, argparse, warnings, re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

# ── Paths & constants ────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DOCS       = ROOT / "docs"
CACHE_TXT  = ROOT / "data" / "meiv2_cache.txt"
DATA_JSON  = DOCS / "mei_data.json"

NOAA_URL   = "https://psl.noaa.gov/enso/mei/data/meiv2.data"
PROXIES    = [
    f"https://api.allorigins.win/raw?url={requests.utils.quote(NOAA_URL)}",
    f"https://corsproxy.io/?url={requests.utils.quote(NOAA_URL)}",
    f"https://api.codetabs.com/v1/proxy?quest={NOAA_URL}",
]

BISEASONS  = ["DJ","JF","FM","MA","AM","MJ","JJ","JA","AS","SO","ON","ND"]
BS_FULL    = ["Dez-Jan","Jan-Fev","Fev-Mar","Mar-Abr","Abr-Mai","Mai-Jun",
              "Jun-Jul","Jul-Ago","Ago-Set","Set-Out","Out-Nov","Nov-Dez"]


# ── 1. Classify ──────────────────────────────────────────────────────────────
def classify(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return {"label": "—", "tier": "neutral"}
    if v >=  2.0: return {"label": "Super El Niño",  "tier": "super"    }
    if v >=  1.5: return {"label": "El Niño Forte",  "tier": "strong"   }
    if v >=  0.5: return {"label": "El Niño",         "tier": "el"       }
    if v <= -1.5: return {"label": "La Niña Forte",  "tier": "la-strong"}
    if v <= -0.5: return {"label": "La Niña",         "tier": "la"       }
    return              {"label": "Neutro",            "tier": "neutral"  }


# ── 2. Fetch ─────────────────────────────────────────────────────────────────
def fetch_mei(dry_run=False, timeout=20):
    """Fetch MEI.v2 raw text. Tries NOAA direct, then proxy fallbacks."""
    if dry_run:
        if CACHE_TXT.exists():
            print(f"  [dry-run] usando cache: {CACHE_TXT}")
            return CACHE_TXT.read_text()
        else:
            raise FileNotFoundError(f"Cache não encontrado: {CACHE_TXT}")

    headers = {
        "User-Agent": "MEI-Monitor/2.0 (celsohlsj@gmail.com)",
        "Accept": "text/plain, */*",
        "Referer": "https://psl.noaa.gov/enso/mei/",
    }

    for label, url in [("NOAA PSL direto", NOAA_URL),
                        *[(f"proxy {i+1}", u) for i, u in enumerate(PROXIES)]]:
        try:
            print(f"  → {label}")
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            text = r.text
            if len(text) < 500 or not re.search(r'^\d{4}\s', text, re.M):
                raise ValueError(f"Resposta inválida ({len(text)} bytes)")
            print(f"  ✓ {len(text):,} bytes recebidos de '{label}'")
            CACHE_TXT.parent.mkdir(parents=True, exist_ok=True)
            CACHE_TXT.write_text(text)
            return text
        except Exception as e:
            print(f"  ⚠ falhou: {e}")

    raise RuntimeError(
        "Todas as fontes falharam. "
        "Faça download manual de https://psl.noaa.gov/enso/mei/data/meiv2.data "
        f"e salve em {CACHE_TXT}"
    )


# ── 3. Parse ─────────────────────────────────────────────────────────────────
def parse_mei(text):
    """Parse NOAA PSL MEI.v2 ASCII table → tidy DataFrame."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or not line[:4].isdigit():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        year = int(parts[0])
        if year < 1979:
            continue
        for i, season in enumerate(BISEASONS):
            try:
                val = float(parts[i + 1])
            except (IndexError, ValueError):
                continue
            if val <= -99.0:
                continue
            rows.append({"year": year, "season": season,
                         "season_full": BS_FULL[i], "mei": round(val, 3)})

    df = (pd.DataFrame(rows)
            .sort_values(["year",
                          pd.Series([BISEASONS.index(s) for s in
                                     pd.DataFrame(rows)["season"]])],
                         ignore_index=True))
    print(f"  ✓ {len(df)} registros  ({df['year'].min()}–{df['year'].max()})")
    return df


# ── 4. Validate ──────────────────────────────────────────────────────────────
def validate(df):
    errors, warnings_list = [], []

    def chk(cond, msg, level="warn"):
        if cond:
            (errors if level == "err" else warnings_list).append(msg)
            print(f"  {'✗' if level=='err' else '⚠'} {msg}")
            return True
        return False

    chk((df["mei"].abs() > 5).sum() > 0,
        f"{(df['mei'].abs()>5).sum()} valor(es) fora do intervalo físico (|MEI|>5)",
        "err")

    dups = df.duplicated(["year","season"]).sum()
    chk(dups > 0, f"{dups} duplicata(s)", "err")

    gaps = sum(
        1 for i in range(1, len(df))
        if (BISEASONS.index(df.iloc[i]["season"]) !=
            (BISEASONS.index(df.iloc[i-1]["season"]) + 1) % 12)
    )
    chk(gaps > 0, f"{gaps} gap(s) temporal(is)")

    jumps = (df["mei"].diff().abs() > 2.0).sum()
    chk(jumps > 0, f"{jumps} salto(s) abruptos(s) > 2.0 unidades")

    passed = len(errors) == 0
    tag = "APROVADA ✓" if passed else "REPROVADA ✗"
    print(f"\n  Validação {tag} — {len(errors)} erro(s), {len(warnings_list)} aviso(s)")
    return {"passed": passed, "errors": errors, "warnings": warnings_list}


# ── 5. SARIMA Sazonal ─────────────────────────────────────────────────────────
def fit_sarima(series, steps=12):
    """
    Seleciona o melhor SARIMA(p,d,q)(P,D,Q,s=12) por AIC e retorna
    model_info e forecasts para os próximos `steps` bi-meses.
    """
    n = len(series)

    # Candidatos ordenados do mais simples ao mais complexo
    candidates = [
        ((0, 1, 1), (0, 1, 1, 12)),   # airline model
        ((1, 1, 1), (0, 1, 1, 12)),
        ((1, 1, 0), (0, 1, 1, 12)),
        ((0, 1, 1), (1, 1, 0, 12)),
        ((1, 1, 1), (1, 1, 0, 12)),
        ((1, 1, 1), (1, 1, 1, 12)),
        ((2, 1, 1), (0, 1, 1, 12)),
        ((1, 1, 2), (0, 1, 1, 12)),
    ]

    best = {"aic": np.inf, "result": None, "order": None, "sorder": None}

    for order, sorder in candidates:
        try:
            mod = SARIMAX(
                series,
                order=order,
                seasonal_order=sorder,
                enforce_stationarity=False,
                enforce_invertibility=False,
                simple_differencing=True,
            )
            res = mod.fit(disp=False, maxiter=400)
            aic = float(res.aic)
            if not np.isnan(aic) and not np.isinf(aic) and aic < best["aic"]:
                best.update(aic=aic, result=res, order=order, sorder=sorder)
        except Exception:
            continue

    if best["result"] is None:
        # Fallback garantido
        mod = SARIMAX(
            series,
            order=(0, 1, 1),
            seasonal_order=(0, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        res = mod.fit(disp=False, maxiter=200)
        best.update(aic=float(res.aic), result=res,
                    order=(0, 1, 1), sorder=(0, 1, 1, 12))

    fc_obj = best["result"].get_forecast(steps=steps)
    means  = fc_obj.predicted_mean.values
    ci95   = fc_obj.conf_int(alpha=0.05).values   # shape (steps, 2)

    forecasts = []
    for h, (pred, lo, hi) in enumerate(zip(means, ci95[:, 0], ci95[:, 1]), 1):
        pred_r = round(float(pred), 3)
        ph = classify(pred_r)
        forecasts.append({
            "step": h,
            "mei":  pred_r,
            "lo":   round(float(lo), 3),
            "hi":   round(float(hi), 3),
            "phase": ph["label"],
            "tier":  ph["tier"],
        })

    o  = best["order"]
    so = best["sorder"]
    print(f"  ✓ SARIMA({o[0]},{o[1]},{o[2]})({so[0]},{so[1]},{so[2]},{so[3]}) "
          f"— AIC={round(best['aic'], 1)}")

    model_info = {
        "type"          : "SARIMA",
        "order"         : list(best["order"]),
        "seasonal_order": list(best["sorder"]),
        "aic"           : round(float(best["aic"]), 3),
        "n"             : n,
        "mu"            : round(float(np.mean(series)), 4),
        "sigma2"        : round(float(np.var(best["result"].resid)), 5),
        # mantido para compatibilidade com build_html.py legado
        "phi": [],
        "rho": [],
    }
    return model_info, forecasts


# ── 6. Statistics ─────────────────────────────────────────────────────────────
def compute_stats(df):
    s = df["mei"]
    df2 = df.copy()
    df2["tier"]  = df2["mei"].map(lambda v: classify(v)["tier"])
    df2["phase"] = df2["mei"].map(lambda v: classify(v)["label"])

    def top_events(df_sorted, n=10):
        return df_sorted.head(n)[["year","season","season_full","mei","phase","tier"]].to_dict("records")

    return {
        "n"            : int(len(df)),
        "year_min"     : int(df["year"].min()),
        "year_max"     : int(df["year"].max()),
        "mean"         : float(round(s.mean(), 4)),
        "std"          : float(round(s.std(),  4)),
        "min_val"      : float(s.min()),
        "max_val"      : float(s.max()),
        "skewness"     : float(round(s.skew(), 4)),
        "kurtosis"     : float(round(s.kurt(), 4)),
        "phase_counts" : df2["tier"].value_counts().to_dict(),
        "top_el"       : top_events(df2.assign(
                             phase=df2["mei"].map(lambda v: classify(v)["label"]),
                             tier =df2["mei"].map(lambda v: classify(v)["tier"]))
                             .sort_values("mei", ascending=False)),
        "top_la"       : top_events(df2.sort_values("mei")),
    }


# ── 7. Export JSON ────────────────────────────────────────────────────────────
def export_json(df, model, forecasts, stats, val_report):
    DOCS.mkdir(parents=True, exist_ok=True)

    df2 = df.copy()
    df2["phase"] = df2["mei"].map(lambda v: classify(v)["label"])
    df2["tier"]  = df2["mei"].map(lambda v: classify(v)["tier"])

    payload = {
        "meta": {
            "source"     : "NOAA Physical Sciences Laboratory — MEI.v2 (JRA-3Q)",
            "url"        : NOAA_URL,
            "description": "Multivariate ENSO Index v2 · bi-monthly 1979–present",
            "variables"  : "SLP, SST, U-wind, V-wind, OLR",
            "region"     : "30°S–30°N, 100°E–70°W",
            "reference"  : "Wolter & Timlin (1993, 1998, 2011)",
            "model_type" : "SARIMA Sazonal",
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "pipeline"   : "YbYrá-BR SARIMA Pipeline",
        },
        "validation"  : val_report,
        "statistics"  : stats,
        "model"       : model,
        "forecasts"   : forecasts,
        "observations": df2.to_dict("records"),
        "recent_48"   : df2.tail(48).to_dict("records"),
    }

    DATA_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  ✓ {DATA_JSON}  ({DATA_JSON.stat().st_size/1024:.1f} KB)")


# ── 8. Main ───────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run",  action="store_true")
    ap.add_argument("--no-model", action="store_true")
    ap.add_argument("--steps",    type=int, default=12,
                    help="Número de bi-meses para prever (default 12)")
    args = ap.parse_args()

    print("\n══════════════════════════════════════")
    print("  MEI.v2 ENSO Pipeline  ·  YbYrá-BR")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("══════════════════════════════════════\n")

    print("[1/5] Fetch")
    text = fetch_mei(dry_run=args.dry_run)

    print("\n[2/5] Parse")
    df = parse_mei(text)

    print("\n[3/5] Validate")
    val = validate(df)

    print("\n[4/5] Modelo SARIMA Sazonal")
    if args.no_model:
        model, forecasts = {}, []
        print("  (pulado)")
    else:
        model, forecasts = fit_sarima(df["mei"].values, steps=args.steps)
        for h in [3, 6, 12]:
            if h <= len(forecasts):
                f = forecasts[h - 1]
                print(f"  +{h:2d} → MEI={f['mei']:+.3f}  {f['phase']}")

    print("\n[5/5] Export JSON")
    stats = compute_stats(df)
    export_json(df, model, forecasts, stats, val)

    print("\n✓ Concluído.\n")
    sys.exit(0 if val["passed"] else 1)


if __name__ == "__main__":
    main()
