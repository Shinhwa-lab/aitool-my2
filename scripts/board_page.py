"""3일차 실습 D — 바이어 리스크 보드 v1. CSV를 읽어 계산하고 HTML 한 장을 쓴다.

실행: `uv run python scripts/board_page.py`
입력(읽기만): labs/day3/lab-d/buyer_board.csv
출력: workbench/day3/outputs/buyer_board.html

모양은 workbench/day3/outputs/design.md 토큰만 쓴다(아래 TOKENS). 같은 입력이면 같은 결과.
첫 화면의 숫자는 여기서(선 17%) 계산해 넣고, 슬라이더를 움직이면 페이지 안 JS가 같은 규칙으로 다시 센다.
"""
import html
import json
import math
from pathlib import Path

import pandas as pd

# design.md 토큰 — 화면의 색 · 글자 · 간격 · 모서리는 이 값만 쓴다
TOKENS = {
    # 색 6개
    "--bg": "#F5F6F8",
    "--surface": "#FFFFFF",
    "--border": "#D9DEE4",
    "--text": "#1B2026",
    "--text-2": "#5A6472",
    "--accent": "#1D4F7A",
    # 등급 색 4개
    "--grade-s": "#1E7344",
    "--grade-a": "#55701A",
    "--grade-b": "#9A5B00",
    "--grade-c": "#B3261E",
    # 글꼴
    "--font": "'Noto Sans KR', sans-serif",
    # 글자 크기 6단계(굵기 / 크기 / 줄 높이)
    "--fs-display": "700 40px/1.15 var(--font)",
    "--fs-display-sm": "700 32px/1.15 var(--font)",
    "--fs-title": "700 28px/1.3 var(--font)",
    "--fs-section": "700 20px/1.4 var(--font)",
    "--fs-body": "400 16px/1.6 var(--font)",
    "--fs-small": "400 14px/1.5 var(--font)",
    # 간격
    "--sp-1": "4px",
    "--sp-2": "8px",
    "--sp-3": "12px",
    "--sp-4": "16px",
    "--sp-5": "24px",
    "--sp-6": "32px",
    "--sp-7": "48px",
    "--sp-8": "64px",
    # 모서리 · 그림자 · 폭
    "--radius-sm": "4px",
    "--radius": "8px",
    "--shadow": "none",
    "--page-max": "1184px",
}

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "labs/day3/lab-d/buyer_board.csv"
OUT = ROOT / "workbench/day3/outputs/buyer_board.html"

AS_OF = "2026-09-30"
LINE0 = 17  # 처음 위험 선(%)
GRADES = ["S", "A", "B", "C"]
LABEL_MIN_SHARE = 0.08  # 분포 막대 칸 안에 글자를 넣는 최소 비중(좁은 칸은 아래 표의 라벨로)

COUNTRY_KO = {
    "ARE": "아랍에미리트", "BRA": "브라질", "CHN": "중국", "DEU": "독일", "EGY": "이집트",
    "GBR": "영국", "IDN": "인도네시아", "IND": "인도", "JPN": "일본", "MEX": "멕시코",
    "MYS": "말레이시아", "NGA": "나이지리아", "NLD": "네덜란드", "POL": "폴란드",
    "SAU": "사우디아라비아", "THA": "태국", "TUR": "튀르키예", "TWN": "대만",
    "USA": "미국", "VNM": "베트남",
}


def grade(pd_30d, line_pct):
    """C부터 검사 — 선 이상 C · 선의 절반 이상 B · 4분의 1 이상 A · 나머지 S."""
    t = line_pct / 100
    if pd_30d >= t:
        return "C"
    if pd_30d >= t / 2:
        return "B"
    if pd_30d >= t / 4:
        return "A"
    return "S"


def money(v):
    return f"${int(round(v)):,}"


def pct(v):
    return f"{v * 100:.1f}%"


def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def compute(df, line_pct):
    g = df["pd_30d"].map(lambda p: grade(p, line_pct))
    total = float(df["open_ar_usd"].sum())
    c = df[g == "C"]
    dist = {k: {"n": int((g == k).sum()), "ar": float(df.loc[g == k, "open_ar_usd"].sum())} for k in GRADES}
    region_c = df[g == "C"].groupby("region")["open_ar_usd"].sum().to_dict()
    return {"grades": g, "c_n": len(c), "c_ar": float(c["open_ar_usd"].sum()), "total": total,
            "dist": dist, "region_c": {k: float(v) for k, v in region_c.items()}}


def render(df, s, regions, top):
    e = html.escape
    n_all = len(df)
    over = df["overdue_usd"]
    over_sum, over_n = float(over.sum()), int((over > 0).sum())

    css_vars = "\n".join(f"    {k}: {v};" for k, v in TOKENS.items())

    def chip(gr, i=None):
        attr = f' data-i="{i}"' if i is not None else ""
        return f'<span class="chip g-{gr}"{attr}>{gr}</span>'

    segs = "".join(
        f'<div class="seg g-{k}" data-g="{k}" style="flex-grow:{s["dist"][k]["n"]}"'
        f'{" hidden" if s["dist"][k]["n"] == 0 else ""}>'
        f'<span>{k + " " + str(s["dist"][k]["n"]) if s["dist"][k]["n"] / n_all >= LABEL_MIN_SHARE else ""}</span></div>'
        for k in GRADES)
    dist_rows = "".join(
        f'<tr><td>{chip(k)}</td><td class="num" data-dn="{k}">{s["dist"][k]["n"]}곳</td>'
        f'<td class="num" data-da="{k}">{money(s["dist"][k]["ar"])}</td></tr>' for k in GRADES)

    top_rows, top_cards = [], []
    for i in top:
        r = df.loc[i]
        gr = s["grades"][i]
        sig = e(r["signal_1"]) if isinstance(r["signal_1"], str) else "–"
        country = COUNTRY_KO[r["country_code"]]
        top_rows.append(
            f'<tr><td class="name">{e(r["buyer_name"])}</td><td>{country}</td><td>{chip(gr, i)}</td>'
            f'<td class="num">{pct(r["pd_30d"])}</td><td class="num">{money(r["open_ar_usd"])}</td>'
            f'<td class="num">{money(r["overdue_usd"])}</td><td>{sig}</td></tr>')
        top_cards.append(
            f'<li class="tcard"><div class="tc-head"><span class="tc-name">{e(r["buyer_name"])}</span>{chip(gr, i)}</div>'
            f'<p class="tc-meta">{country} · {e(r["region"])}</p>'
            f'<dl class="tc-nums"><div><dt>위험 점수</dt><dd class="num">{pct(r["pd_30d"])}</dd></div>'
            f'<div><dt>채권</dt><dd class="num">{money(r["open_ar_usd"])}</dd></div>'
            f'<div><dt>연체</dt><dd class="num">{money(r["overdue_usd"])}</dd></div></dl>'
            f'<p class="tc-sig">{sig}</p></li>')

    rmax = max(a for _, a in regions)
    reg_rows = []
    for name, ar in regions:
        c_ar = s["region_c"].get(name, 0.0)
        reg_rows.append(
            f'<div class="reg" data-r="{e(name)}"><div class="reg-head"><span>{e(name)}</span>'
            f'<span class="num">{money(ar)}</span></div>'
            f'<div class="reg-track"><div class="reg-bar" style="width:{ar / rmax * 100:.4f}%">'
            f'<div class="reg-c" style="width:{c_ar / ar * 100:.4f}%"></div></div></div>'
            f'<p class="reg-note">C등급 <span class="num" data-rc>{money(c_ar)}</span> · '
            f'<span class="num" data-rp>{pct(c_ar / ar)}</span></p></div>')

    data = {
        "line0": LINE0, "n": n_all, "labelMin": LABEL_MIN_SHARE,
        "buyers": [[clean(float(r.pd_30d)), clean(float(r.open_ar_usd)), r.region] for r in df.itertuples()],
        "regions": [[name, ar] for name, ar in regions],
        "base": {"c_n": s["c_n"], "c_ar": s["c_ar"]},
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>바이어 리스크 한눈에</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
{css_vars}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: var(--bg); color: var(--text); }}
  body {{ font: var(--fs-body); word-break: keep-all; overflow-wrap: break-word; }}
  h1, h2, p, ol, dl, dd {{ margin: 0; }}
  .wrap {{ max-width: var(--page-max); margin: 0 auto; padding: 0 var(--sp-7); }}
  .num {{ font-variant-numeric: tabular-nums; white-space: nowrap; text-align: right; }}

  .band {{ background: var(--accent); color: var(--surface); font: var(--fs-small); }}
  .band .wrap {{ padding-top: var(--sp-2); padding-bottom: var(--sp-2); }}
  .head {{ padding-top: var(--sp-7); padding-bottom: var(--sp-6); }}
  .head h1 {{ font: var(--fs-title); color: var(--text); }}
  .head p {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-1); }}

  main {{ display: flex; flex-direction: column; gap: var(--sp-6); }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
           box-shadow: var(--shadow); padding: var(--sp-5); min-width: 0; }}
  .card h2 {{ font: var(--fs-section); color: var(--text); }}
  .sub {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-1); }}

  .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--sp-4); }}
  .k-label {{ font: var(--fs-small); font-weight: 500; color: var(--text-2); }}
  .k-num {{ font: var(--fs-display); color: var(--text); font-variant-numeric: tabular-nums; white-space: nowrap;
            overflow: hidden; margin-top: var(--sp-3); }}
  .k-num.f1 {{ font: var(--fs-display-sm); }}
  .k-num.f2 {{ font: var(--fs-title); }}
  .k-num.f3 {{ font: var(--fs-section); }}
  .k-unit {{ font: var(--fs-small); font-weight: 500; color: var(--text-2); margin-left: var(--sp-1); }}
  .k-note {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-2); }}

  .pair {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: var(--sp-4); }}
  .dist-bar {{ display: flex; gap: var(--sp-1); height: var(--sp-6); margin-top: var(--sp-5); }}
  .seg {{ flex-basis: 0; min-width: var(--sp-1); border-radius: var(--radius-sm); display: flex; align-items: center;
          padding: 0 var(--sp-2); color: var(--surface); font: var(--fs-small); font-weight: 500; white-space: nowrap;
          overflow: hidden; }}
  .seg[hidden] {{ display: none; }}
  .g-S {{ background: var(--grade-s); }}
  .g-A {{ background: var(--grade-a); }}
  .g-B {{ background: var(--grade-b); }}
  .g-C {{ background: var(--grade-c); }}
  .chip {{ display: inline-block; color: var(--surface); font: var(--fs-small); font-weight: 700;
           padding: 0 var(--sp-2); border-radius: var(--radius-sm); }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font: var(--fs-small); font-weight: 500; color: var(--text-2); text-align: left;
        padding: var(--sp-2) var(--sp-3); border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th.num {{ text-align: right; }}
  td {{ padding: var(--sp-3); border-bottom: 1px solid var(--border); color: var(--text); vertical-align: top; }}
  tr:last-child td {{ border-bottom: 0; }}
  .dist-table {{ margin-top: var(--sp-4); }}
  .dist-table td {{ padding: var(--sp-2) var(--sp-3); }}
  .dist-table td:first-child {{ padding-left: 0; }}
  .dist-table td:last-child {{ padding-right: 0; }}

  .line-label {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: var(--sp-5);
                 font: var(--fs-small); color: var(--text-2); }}
  .line-label strong {{ font: var(--fs-title); color: var(--accent); font-variant-numeric: tabular-nums; }}
  input[type=range] {{ width: 100%; margin: var(--sp-3) 0 0; accent-color: var(--accent); }}
  .scale {{ display: flex; justify-content: space-between; font: var(--fs-small); color: var(--text-2); }}
  .delta {{ margin-top: var(--sp-4); padding-top: var(--sp-3); border-top: 1px solid var(--border);
            font: var(--fs-body); font-weight: 500; color: var(--text); }}

  .top {{ margin-top: var(--sp-4); }}
  .top td.name {{ font-weight: 500; }}
  .top-cards {{ display: none; list-style: none; padding: 0; margin-top: var(--sp-4); }}
  .tcard {{ border-top: 1px solid var(--border); padding: var(--sp-4) 0; }}
  .tcard:last-child {{ padding-bottom: 0; }}
  .tc-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: var(--sp-3); }}
  .tc-name {{ font-weight: 500; }}
  .tc-meta {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-1); }}
  .tc-nums {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--sp-2); margin-top: var(--sp-3); }}
  .tc-nums dt {{ font: var(--fs-small); color: var(--text-2); text-align: right; }}
  .tc-nums dd {{ font-weight: 500; }}
  .tc-sig {{ font: var(--fs-small); color: var(--text); margin-top: var(--sp-2); }}

  .regs {{ display: flex; flex-direction: column; gap: var(--sp-4); margin-top: var(--sp-5); }}
  .reg-head {{ display: flex; justify-content: space-between; gap: var(--sp-3); font-weight: 500; }}
  .reg-track {{ margin-top: var(--sp-2); }}
  .reg-bar {{ height: var(--sp-3); background: var(--border); border-radius: var(--radius-sm); overflow: hidden; }}
  .reg-c {{ height: 100%; background: var(--grade-c); }}
  .reg-note {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-1); }}

  .foot {{ font: var(--fs-small); color: var(--text-2); padding-top: var(--sp-7); padding-bottom: var(--sp-7); }}

  @media (max-width: 900px) {{
    .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .pair {{ grid-template-columns: minmax(0, 1fr); }}
  }}
  @media (max-width: 640px) {{
    .wrap {{ padding: 0 var(--sp-4); }}
    .band .wrap {{ padding-top: var(--sp-2); padding-bottom: var(--sp-2); }}
    .head {{ padding-top: var(--sp-5); padding-bottom: var(--sp-5); }}
    main {{ gap: var(--sp-4); }}
    .card {{ padding: var(--sp-4); }}
    .kpis {{ gap: var(--sp-3); }}
    .k-num {{ font: var(--fs-display-sm); }}
    .top {{ display: none; }}
    .top-cards {{ display: block; }}
    .foot {{ padding-top: var(--sp-6); padding-bottom: var(--sp-6); }}
  }}
</style>
</head>
<body>
<div class="band"><div class="wrap">기준일 {AS_OF} · 바이어 {n_all}곳 · 합성 데이터</div></div>
<header class="wrap head">
  <h1>바이어 리스크 한눈에</h1>
  <p>(가상) 한빛정밀(주) 바이어 {n_all}곳 · 합성 데이터</p>
</header>

<main class="wrap">
  <section class="kpis" aria-label="핵심 숫자">
    <div class="card"><p class="k-label">위험 바이어</p>
      <p class="k-num fit"><span id="k-cn">{s["c_n"]}</span><span class="k-unit">곳</span></p>
      <p class="k-note">C등급 · 위험 선 <span id="k-line">{LINE0}%</span> 이상</p></div>
    <div class="card"><p class="k-label">C등급 채권</p>
      <p class="k-num fit" id="k-car">{money(s["c_ar"])}</p>
      <p class="k-note">전체 채권의 <span class="num" id="k-cp">{pct(s["c_ar"] / s["total"])}</span></p></div>
    <div class="card"><p class="k-label">전체 채권</p>
      <p class="k-num fit">{money(s["total"])}</p>
      <p class="k-note">{n_all}곳</p></div>
    <div class="card"><p class="k-label">연체 금액</p>
      <p class="k-num fit">{money(over_sum)}</p>
      <p class="k-note">연체가 있는 곳 {over_n}곳</p></div>
  </section>

  <section class="pair">
    <div class="card">
      <h2>신호등 등급 분포</h2>
      <p class="sub">막대 길이는 곳 수입니다. 등급은 지금 위험 선 기준입니다.</p>
      <div class="dist-bar" role="img" aria-label="등급별 곳 수 막대">{segs}</div>
      <table class="dist-table"><tbody>{dist_rows}</tbody></table>
    </div>
    <div class="card">
      <h2>위험 선</h2>
      <p class="sub">위험 점수가 선 이상이면 C, 선의 절반 이상이면 B, 4분의 1 이상이면 A, 나머지는 S입니다.</p>
      <label class="line-label" for="line">위험 선 <strong id="line-val">{LINE0}%</strong></label>
      <input type="range" id="line" min="5" max="30" step="1" value="{LINE0}">
      <div class="scale"><span>5%</span><span>30%</span></div>
      <p class="delta" id="delta">처음 {LINE0}%와 같습니다</p>
    </div>
  </section>

  <section class="card">
    <h2>위험 상위 10</h2>
    <p class="sub">이번 주에 전화할 곳입니다. 위험 점수가 높은 순서이고, 신호는 확인해 볼 이유입니다.</p>
    <table class="top">
      <thead><tr><th>바이어</th><th>나라</th><th>등급</th><th class="num">위험 점수</th><th class="num">채권</th>
        <th class="num">연체</th><th>위험 신호</th></tr></thead>
      <tbody>{''.join(top_rows)}</tbody>
    </table>
    <ol class="top-cards">{''.join(top_cards)}</ol>
  </section>

  <section class="card">
    <h2>지역별 채권</h2>
    <p class="sub">채권이 많은 지역부터입니다. 막대의 빨간 부분이 지금 C등급인 채권입니다.</p>
    <div class="regs">{''.join(reg_rows)}</div>
  </section>
</main>

<footer class="wrap foot">(가상) 합성 데이터 · 기준일 {AS_OF} · 위험 점수는 판단을 돕는 값이고 결정은 사람이 합니다</footer>

<script id="board-data" type="application/json">{data_json}</script>
<script>
(() => {{
  const D = JSON.parse(document.getElementById('board-data').textContent);
  const money = v => '$' + String(Math.round(v)).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ',');
  const pct = v => (v * 100).toFixed(1) + '%';
  const grade = (p, line) => {{
    const t = line / 100;
    if (p >= t) return 'C';
    if (p >= t / 2) return 'B';
    if (p >= t / 4) return 'A';
    return 'S';
  }};
  const $ = s => document.querySelector(s);
  const $$ = s => Array.from(document.querySelectorAll(s));

  // KPI 숫자가 칸보다 넓으면 한 단계씩 줄인다 — 네 칸이 같은 크기로 함께
  function fit() {{
    const els = $$('.k-num.fit');
    const steps = ['f1', 'f2', 'f3'];
    els.forEach(el => el.classList.remove(...steps));
    for (const c of steps) {{
      if (els.every(el => el.scrollWidth <= el.clientWidth)) break;
      els.forEach(el => {{ el.classList.remove(...steps); el.classList.add(c); }});
    }}
  }}

  function update(line) {{
    const g = D.buyers.map(b => grade(b[0], line));
    const dist = {{S: {{n: 0, ar: 0}}, A: {{n: 0, ar: 0}}, B: {{n: 0, ar: 0}}, C: {{n: 0, ar: 0}}}};
    const regC = {{}};
    let total = 0;
    D.buyers.forEach((b, i) => {{
      dist[g[i]].n += 1; dist[g[i]].ar += b[1]; total += b[1];
      if (g[i] === 'C') regC[b[2]] = (regC[b[2]] || 0) + b[1];
    }});
    const cN = dist.C.n, cAr = dist.C.ar;

    $('#line-val').textContent = line + '%';
    $('#k-line').textContent = line + '%';
    $('#k-cn').textContent = cN;
    $('#k-car').textContent = money(cAr);
    $('#k-cp').textContent = pct(cAr / total);

    $$('.seg').forEach(el => {{
      const k = el.dataset.g, n = dist[k].n;
      el.hidden = n === 0;
      el.style.flexGrow = n;
      el.firstElementChild.textContent = n / D.n >= D.labelMin ? k + ' ' + n : '';
    }});
    $$('[data-dn]').forEach(el => {{ el.textContent = dist[el.dataset.dn].n + '곳'; }});
    $$('[data-da]').forEach(el => {{ el.textContent = money(dist[el.dataset.da].ar); }});

    $$('.chip[data-i]').forEach(el => {{
      const k = g[Number(el.dataset.i)];
      el.className = 'chip g-' + k;
      el.textContent = k;
    }});

    const regTotal = Object.fromEntries(D.regions);
    $$('.reg').forEach(el => {{
      const r = el.dataset.r, c = regC[r] || 0;
      el.querySelector('.reg-c').style.width = (c / regTotal[r] * 100).toFixed(4) + '%';
      el.querySelector('[data-rc]').textContent = money(c);
      el.querySelector('[data-rp]').textContent = pct(c / regTotal[r]);
    }});

    const dn = cN - D.base.c_n, da = cAr - D.base.c_ar;
    const sign = v => (v > 0 ? '+' : v < 0 ? '-' : '±');
    $('#delta').textContent = dn === 0 && Math.round(da) === 0
      ? '처음 ' + D.line0 + '%와 같습니다'
      : '처음 ' + D.line0 + '%보다 C등급 ' + sign(dn) + Math.abs(dn) + '곳 · ' + sign(da) + money(Math.abs(da));
    fit();
  }}

  $('#line').addEventListener('input', e => update(Number(e.target.value)));
  window.addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  fit();
  window.__boardUpdate = update;
}})();
</script>
</body>
</html>
"""


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig")
    unknown = sorted(set(df["country_code"]) - set(COUNTRY_KO))
    if unknown:
        raise ValueError(f"한글 이름이 없는 나라 코드: {unknown}")

    s = compute(df, LINE0)
    match = int((s["grades"] == df["grade"]).sum())
    regions = sorted(df.groupby("region")["open_ar_usd"].sum().items(), key=lambda x: (-x[1], x[0]))
    regions = [(name, float(ar)) for name, ar in regions]
    top = list(df.sort_values(["pd_30d", "buyer_id"], ascending=[False, True], kind="mergesort").index[:10])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(df, s, regions, top), encoding="utf-8")

    print(f"위험 선 {LINE0}% 기준")
    print("  등급별 곳 수:", " · ".join(f"{k} {s['dist'][k]['n']}" for k in GRADES))
    print(f"  C등급 채권 {money(s['c_ar'])} / 전체 채권 {money(s['total'])} ({pct(s['c_ar'] / s['total'])})")
    print(f"  연체 금액 {money(df['overdue_usd'].sum())} · 연체가 있는 곳 {int((df['overdue_usd'] > 0).sum())}곳")
    print(f"  grade 열 일치: {match}/{len(df)}")
    print("  위험 상위 10:", ", ".join(f"{df.loc[i, 'buyer_id']} {pct(df.loc[i, 'pd_30d'])}" for i in top))
    print("  지역별 채권:", " · ".join(f"{n} {money(a)}" for n, a in regions))
    print(f"→ {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size:,} 바이트)")


if __name__ == "__main__":
    main()
