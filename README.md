# YbYrá-BR · Fire Monitor

**Monitoramento automático de focos de incêndio no Brasil com previsão via Facebook Prophet**

[![Update Data](https://github.com/celsohlsj/fire-monitor/actions/workflows/update.yml/badge.svg)](https://github.com/celsohlsj/fire-monitor/actions/workflows/update.yml)

🌐 **GitHub Pages:** `https://celsohlsj.github.io/fire-monitor/`

---

## Visão geral

| Seção | Conteúdo |
|---|---|
| **Fogo** | Focos mensais INPE (1998–presente) por ano e mês |
| **Clima** | Índices oceânicos MEI.v2, AMO (ERSSTv5) e PDO ao vivo (NOAA) |
| **Previsão Prophet** | 12 meses à frente com intervalo de confiança 95% |
| **Dados** | Download CSV / JSON dos dados processados |

---

## Pipeline

```
NOAA PSL  →  scripts/pipeline.py   →  docs/mei_data.json
INPE BDQ  ↘                        ↗
NOAA NCEI  →  scripts/rf_pipeline.py  →  docs/rf_forecast.json
```

### `pipeline.py` — Índices oceânicos (SARIMA)

- Fetch MEI.v2 (NOAA PSL), AMO (NCEI ERSSTv5), PDO (NOAA PSL)
- Ajuste automático de SARIMA sazonal por AIC
- Previsão de 12 bi-meses com IC 95%
- Saída: `docs/mei_data.json`

### `rf_pipeline.py` — Previsão de focos (Prophet)

- Fetch focos mensais INPE via BDQueimadas API
- Regressores oceânicos via previsão SARIMA (MEI lag-1, AMO lag-1, PDO lag-1)
- Facebook Prophet com sazonalidade anual multiplicativa
- Métricas MAPE e MAE (split 80/20)
- Saída: `docs/rf_forecast.json`

### Atualização automática

GitHub Actions executa todo dia **11 de cada mês**. Pode ser disparado manualmente via `workflow_dispatch`.

---

## Estrutura do repositório

```
fire-monitor/
├── .github/workflows/update.yml   # GitHub Actions
├── scripts/
│   ├── pipeline.py                # SARIMA — índices oceânicos
│   └── rf_pipeline.py             # Prophet — previsão de focos
├── docs/
│   ├── index.html                 # Site (GitHub Pages)
│   ├── mei_data.json              # Índices oceânicos + previsão SARIMA
│   └── rf_forecast.json           # Focos + previsão Prophet
├── requirements.txt
└── README.md
```

---

## Uso local

```bash
git clone https://github.com/celsohlsj/fire-monitor
cd fire-monitor
pip install -r requirements.txt

# Índices oceânicos (MEI, AMO, PDO) + SARIMA
python scripts/pipeline.py

# Focos INPE + Prophet
python scripts/rf_pipeline.py

# Modo dry-run (sem fetch externo)
python scripts/rf_pipeline.py --dry-run
```

---

## GitHub Pages

1. **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/docs`
4. Acesse: `https://celsohlsj.github.io/fire-monitor/`

---

## Referências

- Wolter & Timlin (1993, 1998, 2011) — MEI.v2
- Huang et al. (2017) — ERSSTv5 / AMO
- Taylor et al. (2018) — Facebook Prophet · *The American Statistician*
- INPE BDQueimadas — `https://queimadas.dgi.inpe.br`
