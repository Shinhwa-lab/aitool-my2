"""3일차 실습 C — 한빛식당(가상) 밥 예보 페이지. 깨끗한 표로 계산해 HTML 한 장을 쓴다.

실행: `uv run python scripts/lunch_page.py`
입력(읽기만): workbench/day3/outputs/lunch_clean.csv · labs/day3/lab-c/nutritionist_memo.md
출력: workbench/day3/outputs/hanbit_lunch.html

지금 구역: 머리 · 영양사님 감 검증(안내서 「5. 감 검증」). 페이지 규칙은 안내서 「6」.
같은 입력이면 같은 페이지 — 날짜 · 시각 · 난수를 넣지 않는다.
"""
import html
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "workbench/day3/outputs/lunch_clean.csv"
MEMO = ROOT / "labs/day3/lab-c/nutritionist_memo.md"
OUT = ROOT / "workbench/day3/outputs/hanbit_lunch.html"

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"
GAP = 2.0  # 100명당 2명 이상 차이 나면 '차이 있음' — 사람이 정한 선


def load():
    df = pd.read_csv(CLEAN, encoding="utf-8-sig")
    df["per100"] = df["식수"] / df["출근예정"] * 100
    return df


def memo_beliefs():
    """메모의 '제가 믿는 다섯 가지' — 번호 · 굵은 글 · 뒤 문장을 글자 그대로."""
    beliefs = {}
    for line in MEMO.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\d)\. \*\*(.+?)\*\*\s*(.*)$", line)
        if m:
            beliefs[int(m.group(1))] = (m.group(2), m.group(3))
    if sorted(beliefs) != [1, 2, 3, 4, 5]:
        raise ValueError(f"메모에서 믿음 5개를 찾지 못했다: {sorted(beliefs)}")
    return beliefs


def group(rows, label):
    return {"label": label, "value": round(float(rows["per100"].mean()), 1),
            "raw": float(rows["per100"].mean()), "days": int(len(rows))}


def verdict(focus, other, belief_higher):
    """믿음대로 2명 이상 차이 = 맞음 · 2명보다 작음 = 반만 · 반대로 2명 이상 = 틀림."""
    diff = focus["raw"] - other["raw"]
    if abs(diff) < GAP:
        return "반만"
    return "맞음" if (diff > 0) == belief_higher else "틀림"


def compare_sentence(focus, other):
    diff = focus["raw"] - other["raw"]
    word = "많았습니다" if diff > 0 else "적었습니다"
    return f"{focus['label']}이 {other['label']}보다 100명당 {abs(diff):.1f}명 {word}."


def belief_check(df):
    base = df[df["행사"].isna() & (df["월급날"] == 0)]  # 행사 없고 월급날 아닌 날
    beliefs = memo_beliefs()
    cards = []

    def two_way(no, focus_rows, focus_label, other_rows, other_label, belief_higher, extra=""):
        f, o = group(focus_rows, focus_label), group(other_rows, other_label)
        badge = verdict(f, o, belief_higher)
        cards.append({"no": no, "title": beliefs[no][0], "body": beliefs[no][1], "badge": badge,
                      "groups": [f, o], "focus": [0], "note": compare_sentence(f, o) + extra})

    two_way(1, base[base["날씨"] == "비"], "비 오는 날", base[base["날씨"] == "맑음"], "맑은 날", True)
    two_way(2, base[base["요일"] == "금"], "금요일", base[base["요일"] != "금"], "월–목", False)

    # 믿음 3 — 메뉴별(높은 순). 돈가스가 1등이고 2등보다 2명 이상 = 맞음, 1등과 2명 안쪽 = 반만
    menus = (base.groupby("메인메뉴")["per100"].agg(["mean", "count"])
             .sort_values("mean", ascending=False, kind="stable"))
    groups = [{"label": name, "value": round(float(r["mean"]), 1), "raw": float(r["mean"]),
               "days": int(r["count"])} for name, r in menus.iterrows()]
    top, second = groups[0], groups[1]
    don = next(g for g in groups if g["label"] == "돈가스")
    don_rank = groups.index(don) + 1
    if top is don and top["raw"] - second["raw"] >= GAP:
        badge = "맞음"
    elif top["raw"] - don["raw"] < GAP:
        badge = "반만"
    else:
        badge = "틀림"
    if top is don:
        note = f"돈가스가 1등이고, 2등 {second['label']}보다 100명당 {top['raw'] - second['raw']:.1f}명 많았습니다."
    else:
        note = (f"1등은 {top['label']}({top['value']:.1f}명), 돈가스는 {don_rank}등으로 "
                f"1등과 100명당 {top['raw'] - don['raw']:.1f}명 차이였습니다.")
    cards.append({"no": 3, "title": beliefs[3][0], "body": beliefs[3][1], "badge": badge,
                  "groups": groups, "focus": [groups.index(don)], "note": note})

    t = base["최고기온"]
    hot = base[t >= 31]
    two_way(4, hot, "31도 이상", base[(t >= 25) & (t < 31)], "25–31도 미만", False,
            extra=f" 31도 이상인 날은 {len(hot)}일입니다.")
    two_way(5, base[base["요일"] == "월"], "월요일", base[base["요일"].isin(["화", "수", "목"])], "화–목", False)

    # 메모에 없던 규칙 — 월급날(월급날인 날 모두) vs 보통 날
    pay, normal = group(df[df["월급날"] == 1], "월급날"), group(base, "보통 날")
    cards.append({"no": None, "title": "월급날", "body": "메모에 없던 규칙 — 데이터에서 찾은 차이입니다.",
                  "badge": "메모에 없음", "groups": [pay, normal], "focus": [0],
                  "note": compare_sentence(pay, normal)})

    for c in cards:
        for g in c["groups"]:
            g.pop("raw")
    return cards, len(base)


def render(df, cards, n_base):
    start, end = df["날짜"].min(), df["날짜"].max()
    data = {"cards": cards}
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    e = html.escape

    card_html = []
    for i, c in enumerate(cards):
        label = f"믿음 {c['no']}" if c["no"] else "메모에 없던 규칙"
        badge_cls = {"맞음": "ok", "반만": "half", "틀림": "bad"}.get(c["badge"], "plain")
        if len(c["groups"]) == 2:
            a, b = c["groups"]
            nums = (f'<div class="nums"><div><span class="k">{e(a["label"])}</span>'
                    f'<span class="v">{a["value"]:.1f}<small>명</small></span><span class="d">{a["days"]}일</span></div>'
                    f'<div><span class="k">{e(b["label"])}</span>'
                    f'<span class="v muted">{b["value"]:.1f}<small>명</small></span><span class="d">{b["days"]}일</span></div></div>')
            height = 96
        else:
            don = c["groups"][c["focus"][0]]
            top = c["groups"][0]
            nums = (f'<div class="nums"><div><span class="k">{e(don["label"])}</span>'
                    f'<span class="v">{don["value"]:.1f}<small>명</small></span><span class="d">{don["days"]}일</span></div>'
                    f'<div><span class="k">1등 {e(top["label"])}</span>'
                    f'<span class="v muted">{top["value"]:.1f}<small>명</small></span><span class="d">{top["days"]}일</span></div></div>')
            height = 34 * len(c["groups"]) + 30
        card_html.append(f"""
      <article class="card{' extra' if not c['no'] else ''}">
        <div class="card-top"><span class="tag">{label}</span><span class="badge {badge_cls}">{e(c['badge'])}</span></div>
        <h3>{e(c['title'])}</h3>
        <p class="quote">{e(c['body'])}</p>
        {nums}
        <div class="chart" style="height:{height}px"><canvas id="c{i}" aria-label="{e(c['title'])} 막대 그래프"></canvas></div>
        <p class="note">{e(c['note'])}</p>
      </article>""")

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>한빛식당 밥 예보</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<script src="{CHART_JS}"></script>
<style>
  :root {{
    --bg: #f5f6f8; --surface: #ffffff; --ink: #1f2328; --ink-2: #57606a; --line: #e3e6ea;
    --accent: #1d5fd6; --accent-soft: #e6eefb; --warn: #c2410c; --warn-soft: #fbece4;
    --gray: #9aa3ad; --gray-soft: #eef0f2;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: var(--bg); color: var(--ink); }}
  body {{ font-family: 'Noto Sans KR', sans-serif; font-size: 16px; line-height: 1.6;
         word-break: keep-all; overflow-wrap: break-word; }}
  .wrap {{ max-width: 1040px; margin: 0 auto; padding: 0 16px 48px; }}
  header {{ padding: 32px 0 20px; }}
  header h1 {{ margin: 0 0 6px; font-size: 30px; line-height: 1.3; }}
  header p {{ margin: 0; color: var(--ink-2); font-size: 15px; }}
  section {{ margin-top: 24px; }}
  section > h2 {{ font-size: 22px; margin: 0 0 4px; }}
  .lead {{ margin: 0 0 16px; color: var(--ink-2); font-size: 15px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 16px; }}
  .card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 18px;
           display: flex; flex-direction: column; min-width: 0; }}
  .card.extra {{ border-style: dashed; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
  .tag {{ font-size: 14px; color: var(--ink-2); font-weight: 500; }}
  .badge {{ font-size: 14px; font-weight: 700; padding: 2px 12px; border-radius: 999px; white-space: nowrap; }}
  .badge.ok {{ background: var(--accent); color: #fff; }}
  .badge.half {{ background: var(--gray-soft); color: var(--ink-2); border: 1px solid var(--gray); }}
  .badge.bad {{ background: var(--warn); color: #fff; }}
  .badge.plain {{ background: var(--surface); color: var(--ink-2); border: 1px dashed var(--gray); }}
  .card h3 {{ margin: 10px 0 2px; font-size: 18px; line-height: 1.4; }}
  .quote {{ margin: 0 0 12px; color: var(--ink-2); font-size: 15px; }}
  .nums {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }}
  .nums > div {{ display: flex; flex-direction: column; }}
  .k {{ font-size: 14px; color: var(--ink-2); }}
  .v {{ font-size: 26px; font-weight: 700; line-height: 1.2; font-variant-numeric: tabular-nums; }}
  .v small {{ font-size: 14px; font-weight: 500; margin-left: 2px; }}
  .v.muted {{ color: var(--ink-2); }}
  .d {{ font-size: 14px; color: var(--ink-2); }}
  .chart {{ position: relative; width: 100%; }}
  .note {{ margin: 10px 0 0; font-size: 15px; }}
  .nw {{ white-space: nowrap; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>한빛식당 밥 예보</h1>
    <p>(가상) 한빛정밀(주) 본사 구내식당 · 기록 기간 <span class="nw">{start} – {end}</span> · 만든 사람 총무팀 최 대리(가상)</p>
  </header>

  <section id="belief">
    <h2>영양사님 감 검증</h2>
    <p class="lead">숫자는 '출근 100명당 식수'(식수 ÷ 출근예정 × 100)의 평균입니다. 행사가 없고 월급날이 아닌 {n_base}일로 견주었고,
      월급날 카드만 월급날인 날을 모두 썼습니다. 100명당 2명 이상 차이 나면 '차이 있음'으로 봅니다(사람이 정한 선).</p>
    <div class="grid">{''.join(card_html)}
    </div>
  </section>
</div>

<script id="page-data" type="application/json">{data_json}</script>
<script>
  const DATA = JSON.parse(document.getElementById('page-data').textContent);
  const css = getComputedStyle(document.documentElement);
  const ACCENT = css.getPropertyValue('--accent').trim();
  const GRAY = css.getPropertyValue('--gray').trim();
  const INK2 = css.getPropertyValue('--ink-2').trim();
  if (window.Chart) {{
    Chart.defaults.font.family = "'Noto Sans KR', sans-serif";
    Chart.defaults.font.size = 14;
    Chart.defaults.color = INK2;
    DATA.cards.forEach((c, i) => {{
      new Chart(document.getElementById('c' + i), {{
        type: 'bar',
        data: {{
          labels: c.groups.map(g => g.label),
          datasets: [{{
            data: c.groups.map(g => g.value),
            backgroundColor: c.groups.map((g, j) => c.focus.includes(j) ? ACCENT : GRAY),
            borderRadius: 4, borderSkipped: 'start', barThickness: 18
          }}]
        }},
        options: {{
          indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{ label: ctx => {{
              const g = c.groups[ctx.dataIndex];
              return ' 100명당 ' + g.value.toFixed(1) + '명 · ' + g.days + '일';
            }} }} }}
          }},
          scales: {{
            x: {{ min: 0, max: 100, grid: {{ color: '#eef0f2' }}, ticks: {{ stepSize: 25 }} }},
            y: {{ grid: {{ display: false }} }}
          }}
        }}
      }});
    }});
  }}
</script>
</body>
</html>
"""


def main():
    df = load()
    cards, n_base = belief_check(df)
    OUT.write_text(render(df, cards, n_base), encoding="utf-8")

    print(f"보통 날(행사 없고 월급날 아님) {n_base}일")
    for c in cards:
        label = f"믿음 {c['no']}" if c["no"] else "월급날"
        if len(c["groups"]) == 2:
            a, b = c["groups"]
            print(f"  {label}: {a['label']} {a['value']:.1f} ({a['days']}일) vs {b['label']} {b['value']:.1f} ({b['days']}일) → {c['badge']}")
        else:
            ranks = " > ".join(f"{g['label']} {g['value']:.1f}" for g in c["groups"])
            print(f"  {label}: {ranks} → {c['badge']}")
        print(f"     {c['note']}")
    print(f"→ {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size:,} 바이트)")


if __name__ == "__main__":
    main()
