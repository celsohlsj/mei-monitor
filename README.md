# MEI.v2 ENSO Monitor

**Monitoramento automático do El Niño/La Niña via Índice Multivariado MEI.v2**

[![Update MEI.v2 Data](https://github.com/celsohlsj/mei-monitor/actions/workflows/update.yml/badge.svg)](https://github.com/celsohlsj/mei-monitor/actions/workflows/update.yml)

🌐 **GitHub Pages:** `https://fire-monitor.github.io`

---

## O que é o MEI.v2?

O **Multivariate ENSO Index v2** é o índice ENSO mais abrangente da NOAA PSL,
combinando **5 variáveis** simultâneas sobre o Pacífico Tropical (30°S–30°N):

| Variável | Descrição |
|---|---|
| SLP | Pressão ao nível do mar |
| SST | Temperatura da superfície do mar |
| U   | Vento zonal superficial |
| V   | Vento meridional superficial |
| OLR | Radiação de onda longa emergente |

> Wolter & Timlin (1993, 1998, 2011) · JRA-3Q Reanalysis · 1979–presente

---

## Pipeline

```
NOAA PSL (meiv2.data)
        ↓  scripts/pipeline.py
   Fetch → Parse → Validate → AR(p) Model → docs/mei_data.json
        ↓  scripts/build_html.py
              docs/index.html  (GitHub Pages)
```

### Atualização automática

O GitHub Actions executa todo dia **11 de cada mês** (1 dia após a atualização
da NOAA). Também pode ser disparado manualmente via `workflow_dispatch`.

---

## Estrutura do repositório

```
mei-monitor/
├── .github/workflows/update.yml   # GitHub Actions
├── scripts/
│   ├── pipeline.py                # Fetch + Validate + AR(p) + JSON
│   └── build_html.py              # JSON → index.html estático
├── docs/
│   ├── index.html                 # Página pública (GitHub Pages)
│   └── mei_data.json              # Dados processados (gerado automaticamente)
├── data/
│   └── meiv2_cache.txt            # Cache local do arquivo NOAA
├── requirements.txt
└── README.md
```

---

## Uso local

```bash
git clone https://github.com/celsohlsj/mei-monitor
cd mei-monitor
pip install -r requirements.txt

# Pipeline completo (fetch + modelo + JSON + HTML)
python scripts/pipeline.py
python scripts/build_html.py

# Apenas validar dados cacheados
python scripts/pipeline.py --dry-run --no-model

# Opções
python scripts/pipeline.py --steps 24 --max-ar 8
```

---

## GitHub Pages

1. Vá em **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/docs`
4. Acesse: `https://<seu-usuario>.github.io/mei-monitor/`

---

## Referências

- Wolter, K., & Timlin, M.S. (1993). *Proc. 17th Climate Diagnostics Workshop*
- Wolter, K., & Timlin, M.S. (1998). *Weather, 53*, 315–324
- Wolter, K., & Timlin, M.S. (2011). *Int. J. Climatology, 31*, 1074–1087
- Zhang et al. (2019). *Geophys. Res. Lett., 46*

---

Desenvolvido para **IPAM / UFMA** · Celso H. L. Silva-Junior
