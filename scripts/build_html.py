#!/usr/bin/env python3
"""
Build docs/index.html from docs/mei_data.json
Generates a fully self-contained static page for GitHub Pages.
"""
import json
from pathlib import Path
from datetime import datetime

ROOT      = Path(__file__).parent.parent
DATA_JSON = ROOT / "docs" / "mei_data.json"
OUT_HTML  = ROOT / "docs" / "index.html"

def load_json():
    if not DATA_JSON.exists():
        raise FileNotFoundError(f"Run pipeline.py first — {DATA_JSON} not found.")
    return json.loads(DATA_JSON.read_text())

def phase_color(tier):
    return {
        "super"    : "#ffd700",
        "strong"   : "#ff6a00",
        "el"       : "#ff3d00",
        "la-strong": "#0080ff",
        "la"       : "#1c8fff",
    }.get(tier, "#6a8ca8")

def build_html(d):
    meta        = d["meta"]
    stats       = d["statistics"]
    model       = d.get("model", {})
    forecasts   = d.get("forecasts", [])
    recent      = d.get("recent_48", [])
    val         = d.get("validation", {})
    last        = recent[-1] if recent else {}
    last_mei    = last.get("mei", 0)
    last_phase  = last.get("phase", "—")
    last_tier   = last.get("tier", "neutral")
    last_season = f"{last.get('season_full','')} {last.get('year','')}"
    fc6  = forecasts[5]  if len(forecasts) > 5  else {}
    fc12 = forecasts[11] if len(forecasts) > 11 else {}
    fc24 = forecasts[23] if len(forecasts) > 23 else {}
    updated = meta.get("updated_utc","")[:16].replace("T"," ") + " UTC"

    obs_js   = json.dumps(d.get("observations", []))
    fc_js    = json.dumps(forecasts)
    top_el_js = json.dumps(stats["top_el"])
    top_la_js = json.dumps(stats["top_la"])

    lc = phase_color(last_tier)
    fc6c  = phase_color(fc6.get("tier","neutral"))
    fc12c = phase_color(fc12.get("tier","neutral"))

    val_badge = ("✓ Aprovada" if val.get("passed") else "⚠ Com erros")
    val_color = "#3ddc84" if val.get("passed") else "#ff6a00"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="MEI.v2 ENSO Monitor — Índice Multivariado ENSO · NOAA PSL · IPAM/UFMA">
<meta property="og:title" content="MEI.v2 ENSO Monitor · IPAM/UFMA">
<meta property="og:description" content="Monitoramento do El Niño/La Niña via MEI.v2 Multivariado — NOAA PSL">
<title>MEI.v2 · ENSO Monitor · IPAM/UFMA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#03080e;--panel:#070e18;--border:#0f2030;
  --el-super:#ffd700;--el-strong:#ff6a00;--el:#ff3d00;
  --la:#1c8fff;--neutral:#6a8ca8;--accent:#e8b84b;
  --text:#bcd4e6;--dim:#2e4a60;--green:#3ddc84;
  --font-mono:'Space Mono','Courier New',monospace;
  --font-sans:'Syne','Arial Black',sans-serif;
}}
html,body{{min-height:100%;background:var(--bg);color:var(--text);
  font-family:var(--font-mono);font-size:13px}}
::-webkit-scrollbar{{width:4px;height:4px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.3;transform:scale(.7)}}}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}

/* Header */
.hdr{{background:var(--panel);border-bottom:1px solid var(--border);
  padding:16px 20px 12px}}
.hdr-inner{{max-width:1100px;margin:0 auto;display:flex;align-items:flex-start;
  justify-content:space-between;flex-wrap:wrap;gap:10px}}
.h1{{font-family:var(--font-sans);font-size:clamp(1.3rem,3vw,2rem);
  font-weight:800;letter-spacing:-.02em;color:#fff}}
.h1 span{{color:var(--accent)}}
.h-sub{{font-size:9px;color:var(--dim);letter-spacing:.13em;
  text-transform:uppercase;margin-top:5px}}
.badge{{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;
  border-radius:3px;font-size:10px;font-weight:700;letter-spacing:.07em;
  font-family:var(--font-mono)}}
.dot{{width:6px;height:6px;border-radius:50%;animation:pulse 1.8s infinite}}

/* Body */
.body{{max-width:1100px;margin:0 auto;padding:16px}}

/* Cards */
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));
  gap:10px;margin-bottom:14px}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:4px;
  padding:13px 15px;position:relative;overflow:hidden}}
.card-top{{position:absolute;top:0;left:0;right:0;height:2px}}
.card-lbl{{font-size:9px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--dim);margin-bottom:6px}}
.card-val{{font-family:var(--font-sans);font-size:1.65rem;font-weight:800;line-height:1}}
.card-sub{{font-size:10px;color:var(--dim);margin-top:5px;line-height:1.5;white-space:pre-line}}

/* Tabs */
.tabs{{border-bottom:1px solid var(--border);display:flex;
  gap:0;margin-bottom:16px;overflow-x:auto}}
.tab{{padding:7px 14px;background:none;border:none;
  border-bottom:2px solid transparent;color:var(--dim);
  font-family:var(--font-mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;cursor:pointer;transition:all .15s;margin-bottom:-1px}}
.tab.active{{color:var(--accent);border-bottom-color:var(--accent)}}

/* Panels */
.panel{{background:var(--panel);border:1px solid var(--border);
  border-radius:4px;padding:14px 16px;margin-bottom:12px}}
.sec-title{{font-size:9px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--dim);margin-bottom:10px;font-weight:700;
  display:flex;align-items:center;gap:8px;flex-wrap:wrap}}

/* Chart */
.chart-wrap{{position:relative;height:260px;margin-bottom:8px}}

/* Legend */
.legend{{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px}}
.leg-item{{display:flex;align-items:center;gap:6px;font-size:9px;color:var(--dim)}}
.leg-dot{{width:9px;height:9px;border-radius:50%}}

/* Table */
.tbl-wrap{{overflow-y:auto;max-height:420px}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
th{{padding:6px 8px;color:var(--dim);font-size:9px;letter-spacing:.1em;
  text-transform:uppercase;border-bottom:1px solid var(--border);
  text-align:left;position:sticky;top:0;background:var(--panel)}}
td{{padding:5px 8px;border-bottom:1px solid #0f203022}}
tr:nth-child(even) td{{background:#0f203020}}

/* Grid 2 */
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
@media(max-width:600px){{.g2{{grid-template-columns:1fr}}}}

/* Rank bar */
.rank-row{{display:flex;align-items:center;gap:8px;
  padding:5px 0;border-bottom:1px solid #0f203025}}
.rank-bar-wrap{{flex:1;height:5px;background:var(--border);
  border-radius:3px;overflow:hidden}}
.rank-bar{{height:100%;border-radius:3px;transition:width .5s ease}}

/* Model grid */
.model-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.param-lbl{{font-size:9px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--dim);margin-bottom:3px}}
.param-val{{font-family:var(--font-sans);font-size:1.05rem;font-weight:800}}

/* Info box */
.info{{font-size:10px;color:var(--dim);line-height:1.7;
  border-top:1px solid var(--border);padding-top:10px;margin-top:10px}}

/* Footer */
footer{{font-size:9px;color:var(--dim);letter-spacing:.1em;
  text-transform:uppercase;text-align:center;
  border-top:1px solid var(--border);padding-top:12px;margin-top:16px}}

/* Tab content */
.tab-pane{{display:none}}
.tab-pane.active{{display:block}}

/* Updated badge */
.upd{{font-size:9px;color:var(--dim);margin-top:4px}}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-inner">
    <div>
      <h1 class="h1">MEI<span>.v2</span> ENSO Monitor</h1>
      <p class="h-sub">
        Multivariate ENSO Index v2 · NOAA Physical Sciences Laboratory ·
        JRA-3Q Reanalysis · Wolter &amp; Timlin (1993–2011)
      </p>
      <p class="upd">Dados: {updated} · Pipeline Python/IPAM/UFMA</p>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
      <span class="badge" style="background:{lc}18;border:1px solid {lc}50;color:{lc}">
        <span class="dot" style="background:{lc}"></span>
        NOAA PSL · Dado Oficial
      </span>
      <span class="badge" style="background:{lc}18;border:1px solid {lc}50;color:{lc}">
        {last_phase} · MEI {"+" if last_mei > 0 else ""}{last_mei:.3f}
      </span>
      <span class="badge" style="background:{val_color}18;border:1px solid {val_color}50;color:{val_color}">
        {val_badge}
      </span>
    </div>
  </div>
</div>

<div class="body">

<!-- STATUS CARDS -->
<div class="cards">
  <div class="card">
    <div class="card-top" style="background:{lc}"></div>
    <div class="card-lbl">Fase Atual (MEI)</div>
    <div class="card-val" style="color:{lc}">{last_phase.split()[0]}</div>
    <div class="card-sub">{last_season}\\nMEI = {"+" if last_mei > 0 else ""}{last_mei:.3f}</div>
  </div>
  <div class="card">
    <div class="card-top" style="background:{lc}"></div>
    <div class="card-lbl">Último MEI.v2</div>
    <div class="card-val" style="color:{lc}">{"+" if last_mei > 0 else ""}{last_mei:.3f}</div>
    <div class="card-sub">{last_season}\\n5 vars: SLP SST U V OLR</div>
  </div>
  <div class="card">
    <div class="card-top" style="background:{fc6c}"></div>
    <div class="card-lbl">Previsão AR +6 bi-meses</div>
    <div class="card-val" style="color:{fc6c}">{"+" if fc6.get("mei",0) > 0 else ""}{fc6.get("mei","—")}</div>
    <div class="card-sub">{fc6.get("phase","—")}\\nIC95%: [{fc6.get("lo","—")}, {fc6.get("hi","—")}]</div>
  </div>
  <div class="card">
    <div class="card-top" style="background:{fc12c}"></div>
    <div class="card-lbl">Previsão AR +12 bi-meses</div>
    <div class="card-val" style="color:{fc12c}">{"+" if fc12.get("mei",0) > 0 else ""}{fc12.get("mei","—")}</div>
    <div class="card-sub">{fc12.get("phase","—")}\\nModelo AR({model.get("order","?")})</div>
  </div>
  <div class="card">
    <div class="card-top" style="background:var(--green)"></div>
    <div class="card-lbl">Registros</div>
    <div class="card-val" style="color:var(--green)">{stats["n"]}</div>
    <div class="card-sub">{stats["year_min"]}–{stats["year_max"]}\\n{val_badge}</div>
  </div>
</div>

<!-- TABS -->
<div class="tabs">
  <button class="tab active" onclick="showTab('serie',this)">Série Histórica</button>
  <button class="tab" onclick="showTab('tabela',this)">Tabela</button>
  <button class="tab" onclick="showTab('ranking',this)">Ranking</button>
  <button class="tab" onclick="showTab('modelo',this)">Modelo AR({model.get("order","?")})</button>
  <button class="tab" onclick="showTab('sobre',this)">Sobre</button>
</div>

<!-- SÉRIE -->
<div id="tab-serie" class="tab-pane active">
  <div class="panel">
    <div class="sec-title">
      MEI.v2 · Série Histórica Bi-mensal
      <span class="badge" style="background:var(--accent)18;border:1px solid var(--accent)50;color:var(--accent)">NOAA PSL</span>
      <span class="badge" style="background:#1c8fff18;border:1px solid #1c8fff50;color:#1c8fff">+ Previsão AR</span>
      <select id="yearSel" onchange="redrawChart()"
        style="margin-left:auto;background:var(--panel);border:1px solid var(--border);
          border-radius:3px;color:var(--text);font-family:var(--font-mono);
          font-size:10px;padding:4px 8px;cursor:pointer">
        <option value="all">Todo período (1979–)</option>
        <option value="30">Últimos 30 anos</option>
        <option value="20" selected>Últimos 20 anos</option>
        <option value="10">Últimos 10 anos</option>
      </select>
    </div>
    <div class="chart-wrap"><canvas id="mainChart"></canvas></div>
    <div class="legend">
      <div class="leg-item"><div class="leg-dot" style="background:var(--el)"></div>El Niño (≥+0.5)</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--el-super)"></div>Super El Niño (≥+2.0)</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--la)"></div>La Niña (≤−0.5)</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--neutral)"></div>Neutro</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--accent)"></div>Previsão AR</div>
    </div>
  </div>
</div>

<!-- TABELA -->
<div id="tab-tabela" class="tab-pane">
  <div class="panel">
    <div class="sec-title">Últimos 48 bi-meses observados</div>
    <div class="tbl-wrap">
      <table id="obsTable">
        <thead><tr>
          <th>Bi-mês</th><th>Temporada</th><th>Ano</th>
          <th>MEI</th><th>Fase</th><th>Intensidade</th>
        </tr></thead>
        <tbody id="obsBody"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- RANKING -->
<div id="tab-ranking" class="tab-pane">
  <div class="g2">
    <div class="panel">
      <div class="sec-title" style="color:var(--el)">🌡 Top El Niño — MEI.v2</div>
      <div id="topEl"></div>
    </div>
    <div class="panel">
      <div class="sec-title" style="color:var(--la)">❄ Top La Niña — MEI.v2</div>
      <div id="topLa"></div>
    </div>
  </div>
</div>

<!-- MODELO -->
<div id="tab-modelo" class="tab-pane">
  <div class="g2">
    <div class="panel">
      <div class="sec-title">Parâmetros AR({model.get("order","?")})</div>
      <div class="model-grid" id="modelParams"></div>
      <div class="info">
        Ordem selecionada por AIC. Coeficientes estimados pelas equações de
        Yule-Walker. Intervalo de confiança 95% com expansão proporcional ao
        horizonte (×0.10 por passo).
      </div>
    </div>
    <div class="panel">
      <div class="sec-title">Previsão — Próximos {len(forecasts)} bi-meses</div>
      <div class="tbl-wrap" style="max-height:360px">
        <table>
          <thead><tr>
            <th>Passo</th><th>MEI</th><th>Lo (IC95%)</th>
            <th>Hi (IC95%)</th><th>Fase</th>
          </tr></thead>
          <tbody id="fcBody"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- SOBRE -->
<div id="tab-sobre" class="tab-pane">
  <div class="panel">
    <div class="sec-title">Sobre o MEI.v2</div>
    <div class="info" style="font-size:11px;color:var(--text)">
      <p style="margin-bottom:10px">
        O <strong>Multivariate ENSO Index v2 (MEI.v2)</strong> é a série temporal
        do primeiro EOF combinado de cinco variáveis sobre o Pacífico Tropical
        (30°S–30°N, 100°E–70°W): pressão ao nível do mar (SLP), temperatura
        da superfície do mar (SST), vento zonal (U), vento meridional (V) e
        radiação de onda longa emergente (OLR).
      </p>
      <p style="margin-bottom:10px">
        Por integrar variáveis oceânicas e atmosféricas simultaneamente, o MEI é
        considerado o índice ENSO mais abrangente. Valores positivos indicam
        El Niño; negativos indicam La Niña. Limiares convencionais: ±0.5 (fraco),
        ±1.0 (moderado), ±1.5 (forte), ±2.0 (super).
      </p>
      <p style="margin-bottom:10px">
        <strong>Fonte de dados:</strong>
        <a href="https://psl.noaa.gov/enso/mei/" target="_blank">NOAA Physical Sciences Laboratory</a>
        — atualizado mensalmente até o dia 10. Série JRA-3Q desde 2024 (r=0.999 com JRA-55).
      </p>
      <p style="margin-bottom:10px">
        <strong>Pipeline:</strong> Python (NumPy, Pandas, Requests) + GitHub Actions.
        Fetch automático diário → validação → modelo AR(p) via Yule-Walker →
        exportação JSON → rebuild do HTML estático.
      </p>
      <p>
        <strong>Referências:</strong><br>
        Wolter &amp; Timlin (1993) · Wolter &amp; Timlin (1998) · Wolter &amp; Timlin (2011) ·
        Zhang et al. (2019)
      </p>
    </div>
    <div class="info" style="margin-top:12px">
      <strong>Validação:</strong>
      Erros: {len(val.get("errors",[]))} · Avisos: {len(val.get("warnings",[]))}
      {(" · " + " / ".join(val.get("warnings",[])) if val.get("warnings") else "")}
    </div>
    <div class="info" style="margin-top:12px">
      <strong>Estatísticas:</strong>
      n={stats["n"]} · μ={stats["mean"]} · σ={stats["std"]} ·
      min={stats["min_val"]} · max={stats["max_val"]} ·
      skew={stats["skewness"]} · kurt={stats["kurtosis"]}
    </div>
  </div>
</div>

<!-- FOOTER -->
<footer>
  Fonte:
  <a href="https://psl.noaa.gov/enso/mei/" target="_blank">NOAA PSL — MEI.v2 (JRA-3Q)</a>
  · Wolter &amp; Timlin (1993, 1998, 2011) ·
  Região: 30°S–30°N · Variáveis: SLP SST U V OLR
  <br>
  Pipeline Python · GitHub Actions · Desenvolvido para IPAM / UFMA ·
  <a href="https://github.com/celsohlsj" target="_blank">Celso H. L. Silva-Junior</a>
  · {updated}
</footer>

</div><!-- /body -->

<script>
// ── Data injected from Python ─────────────────────────────────────────────
const OBS      = {obs_js};
const FC       = {fc_js};
const TOP_EL   = {top_el_js};
const TOP_LA   = {top_la_js};
const MODEL    = {json.dumps(model)};
const STATS    = {json.dumps(stats)};

// ── Helpers ──────────────────────────────────────────────────────────────
const C = {{
  elSuper:"#ffd700", elStrong:"#ff6a00", el:"#ff3d00",
  la:"#1c8fff", neutral:"#6a8ca8", accent:"#e8b84b",
  text:"#bcd4e6", dim:"#2e4a60", panel:"#070e18", border:"#0f2030"
}};

function meiColor(v) {{
  if (v >=  2.0) return C.elSuper;
  if (v >=  1.5) return C.elStrong;
  if (v >=  0.5) return C.el;
  if (v <= -0.5) return C.la;
  return C.neutral;
}}

function fmt(v, p=3) {{
  if (v===undefined||v===null) return "—";
  return (v>0?"+":"")+v.toFixed(p);
}}

function badge(color, text) {{
  return `<span class="badge" style="background:${{color}}18;border:1px solid ${{color}}50;color:${{color}}">${{text}}</span>`;
}}

// ── Tabs ─────────────────────────────────────────────────────────────────
function showTab(id, btn) {{
  document.querySelectorAll(".tab-pane").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
  document.getElementById("tab-"+id).classList.add("active");
  btn.classList.add("active");
  if (id==="serie") setTimeout(redrawChart, 50);
}}

// ── Chart.js main chart ───────────────────────────────────────────────────
let mainChartInst = null;

function redrawChart() {{
  const sel = document.getElementById("yearSel").value;
  const now = new Date().getFullYear();
  const filtered = sel==="all" ? OBS : OBS.filter(d=>d.year>=now-parseInt(sel));

  const labels    = filtered.map(d=>`${{d.season}} ${{d.year}}`);
  const vals      = filtered.map(d=>d.mei);
  const ptColors  = vals.map(v=>meiColor(v));

  // forecast extension
  const fcLabels  = FC.map(f=>`FC+${{f.step}}`);
  const fcVals    = FC.map(f=>f.mei);
  const fcHi      = FC.map(f=>f.hi);
  const fcLo      = FC.map(f=>f.lo);
  const allLabels = [...labels, ...fcLabels];
  const nObs      = labels.length;

  if (mainChartInst) mainChartInst.destroy();

  const ctx = document.getElementById("mainChart").getContext("2d");
  mainChartInst = new Chart(ctx, {{
    type: "line",
    data: {{
      labels: allLabels,
      datasets: [
        // CI upper (fill to lower)
        {{
          label:"IC Hi", data:[...Array(nObs).fill(null),...fcHi],
          borderWidth:0, pointRadius:0, fill:"+1",
          backgroundColor:"rgba(232,184,75,0.10)", tension:0.4, order:10
        }},
        // CI lower
        {{
          label:"IC Lo", data:[...Array(nObs).fill(null),...fcLo],
          borderWidth:0, pointRadius:0, fill:false, tension:0.4, order:11
        }},
        // Forecast line
        {{
          label:"Previsão AR",
          data:[...Array(nObs).fill(null),...fcVals],
          borderColor:"rgba(232,184,75,0.9)", borderWidth:2, borderDash:[7,4],
          pointRadius:3, pointBackgroundColor:fcVals.map(v=>meiColor(v)),
          tension:0.4, fill:false, order:2
        }},
        // Observed
        {{
          label:"MEI Observado", data:[...vals,...Array(FC.length).fill(null)],
          borderColor:"rgba(188,212,230,0.5)", borderWidth:1.3,
          pointRadius:vals.length<300?2:0,
          pointBackgroundColor:ptColors,
          tension:0.25, fill:false, order:1
        }}
      ]
    }},
    options: {{
      responsive:true, maintainAspectRatio:false,
      interaction:{{mode:"index",intersect:false}},
      plugins:{{
        legend:{{display:false}},
        tooltip:{{
          backgroundColor:"#070e18", borderColor:"#0f2030", borderWidth:1,
          titleColor:"#bcd4e6", bodyColor:"#6a8ca8",
          titleFont:{{family:"Space Mono",size:10}},
          bodyFont:{{family:"Space Mono",size:10}},
          callbacks:{{
            label: ctx => {{
              const v = ctx.parsed.y;
              if (v===null) return null;
              if (ctx.dataset.label==="IC Hi"||ctx.dataset.label==="IC Lo") return null;
              let ph="—";
              if (v>=2) ph="Super El Niño";
              else if (v>=1.5) ph="El Niño Forte";
              else if (v>=0.5) ph="El Niño";
              else if (v<=-1.5) ph="La Niña Forte";
              else if (v<=-0.5) ph="La Niña";
              else ph="Neutro";
              return ` ${{ctx.dataset.label}}: ${{fmt(v)}} — ${{ph}}`;
            }}
          }}
        }}
      }},
      scales:{{
        x:{{
          grid:{{color:"rgba(15,32,48,0.7)"}},
          ticks:{{color:"#2e4a60",font:{{family:"Space Mono",size:8}},
            maxTicksLimit:20,maxRotation:45}}
        }},
        y:{{
          grid:{{color:"rgba(15,32,48,0.7)"}},
          ticks:{{color:"#2e4a60",font:{{family:"Space Mono",size:9}},
            callback:v=>(v>0?"+":"")+v.toFixed(1)+"°"}}
        }}
      }}
    }},
    plugins:[{{
      id:"thresholds",
      afterDraw(chart) {{
        const {{ctx:c,chartArea:ca,scales}} = chart;
        if (!ca) return;
        c.save();
        [[0.5,"#ff3d00"],[- 0.5,"#1c8fff"],[2.0,"#ffd700"],[-1.5,"#1c8fff"]].forEach(([v,col])=>{{
          const y = scales.y.getPixelForValue(v);
          c.beginPath(); c.strokeStyle=col+"55"; c.lineWidth=.9;
          c.setLineDash([4,4]); c.moveTo(ca.left,y); c.lineTo(ca.right,y); c.stroke();
          c.setLineDash([]);
          c.fillStyle=col+"88"; c.font="8px Space Mono";
          c.fillText((v>0?"+":"")+v, ca.right+4, y+3);
        }});
        c.restore();
      }}
    }}]
  }});
}}

// ── Table ─────────────────────────────────────────────────────────────────
function buildTable() {{
  const rows = [...OBS].reverse().slice(0,48);
  document.getElementById("obsBody").innerHTML = rows.map((d,i)=>{{
    const col = meiColor(d.mei);
    const int = Math.abs(d.mei)>=2?"Super":Math.abs(d.mei)>=1.5?"Forte":
                Math.abs(d.mei)>=0.5?"Moderado":"Fraco/Neutro";
    return `<tr>
      <td>${{d.season}}</td><td>${{d.season_full}}</td><td>${{d.year}}</td>
      <td style="color:${{col}};font-weight:700">${{fmt(d.mei)}}</td>
      <td>${{badge(col,d.phase)}}</td>
      <td style="color:var(--dim)">${{int}}</td>
    </tr>`;
  }}).join("");
}}

// ── Rankings ──────────────────────────────────────────────────────────────
function buildRank(data, elId) {{
  const maxV = Math.max(...data.map(d=>Math.abs(d.mei)));
  document.getElementById(elId).innerHTML = data.map((d,i)=>{{
    const col = meiColor(d.mei);
    const pct = Math.min(100, Math.abs(d.mei/maxV)*100);
    return `<div class="rank-row">
      <span style="color:var(--dim);font-size:10px;width:18px">${{i+1}}.</span>
      <span style="font-size:10px;width:22px;color:var(--dim)">${{d.season}}</span>
      <span style="font-size:10px;width:36px">${{d.year}}</span>
      <div class="rank-bar-wrap">
        <div class="rank-bar" style="width:${{pct}}%;background:${{col}}"></div>
      </div>
      <span style="color:${{col}};font-weight:700;font-size:12px;width:50px;text-align:right">
        ${{fmt(d.mei,2)}}
      </span>
    </div>`;
  }}).join("");
}}

// ── Model params ──────────────────────────────────────────────────────────
function buildModel() {{
  const rows = [
    ["Ordem",    `AR(${{MODEL.order}})`,    "#e8b84b"],
    ["μ média",  fmt(MODEL.mu,4),           meiColor(MODEL.mu)],
    ["σ² resid.", MODEL.sigma2,             "var(--dim)"],
    ["AIC",      MODEL.aic,                 "var(--dim)"],
    ["ρ₁ autocorr.", MODEL.rho?.[0]??"-",  "var(--text)"],
    ["ρ₂ autocorr.", MODEL.rho?.[1]??"-",  "var(--text)"],
    ["n série",  MODEL.n,                   "#3ddc84"],
    ["Horizonte",`${{FC.length}} bi-meses`, "#1c8fff"],
    ...MODEL.phi.map((v,i)=>[`φ${{i+1}} (lag-${{i+1}})`, fmt(v,5), "var(--text)"])
  ];
  document.getElementById("modelParams").innerHTML = rows.map(([l,v,c])=>`
    <div>
      <div class="param-lbl">${{l}}</div>
      <div class="param-val" style="color:${{c}}">${{v}}</div>
    </div>`).join("");

  document.getElementById("fcBody").innerHTML = FC.map((f,i)=>{{
    const col = meiColor(f.mei);
    return `<tr>
      <td style="color:var(--dim)">+${{f.step}}</td>
      <td style="color:${{col}};font-weight:700">${{fmt(f.mei)}}</td>
      <td style="color:var(--dim)">${{f.lo}}</td>
      <td style="color:var(--dim)">${{f.hi}}</td>
      <td>${{badge(col,f.phase)}}</td>
    </tr>`;
  }}).join("");
}}

// ── Init ──────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {{
  buildTable();
  buildRank(TOP_EL, "topEl");
  buildRank(TOP_LA, "topLa");
  buildModel();
  setTimeout(redrawChart, 100);
}});
</script>
</body>
</html>"""
    return html

def main():
    print("Carregando mei_data.json…")
    d = load_json()
    print("Gerando HTML…")
    html = build_html(d)
    OUT_HTML.write_text(html, encoding="utf-8")
    kb = OUT_HTML.stat().st_size / 1024
    print(f"✓ {OUT_HTML}  ({kb:.0f} KB)")

if __name__ == "__main__":
    main()
