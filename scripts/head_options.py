"""3일차 실습 D — 보드 머리(제목 + KPI 4칸)를 세 가지 스타일로 나란히 보여 주는 비교 페이지.

실행: `uv run python scripts/head_options.py`
입력(읽기만): labs/day3/lab-d/buyer_board.csv — 숫자는 scripts/board_page.py의 계산을 그대로 불러 쓴다
출력: workbench/day3/outputs/head_options.html

buyer_board.html과 design.md는 고치지 않는다(사람이 한 안을 고르면 그때 v2로).
"""
import html
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import board_page as bp  # noqa: E402
from design_contrast import contrast  # noqa: E402

OUT = bp.ROOT / "workbench/day3/outputs/head_options.html"
SANS = "'Noto Sans KR', sans-serif"
SERIF = "'Noto Serif KR', serif"

# 안마다 머리 영역에서 쓰는 값 — 바탕과 글자색을 짝으로 직접 정한다(바깥 색을 물려받지 않게)
OPTIONS = [
    {
        "key": "a", "label": "A", "name": "밝은 미니멀",
        "vars": {
            "--o-bg": "#FFFFFF", "--o-card": "#F5F6F8", "--o-line": "#D9DEE4",
            "--o-text": "#1B2026", "--o-text-2": "#5A6472",
            "--o-band-bg": "#1D4F7A", "--o-band-text": "#FFFFFF",
            "--o-title": f"700 32px/1.25 {SANS}",
            "--o-num": f"700 48px/1.1 {SANS}", "--o-num-1": f"700 40px/1.1 {SANS}",
            "--o-num-2": f"700 32px/1.1 {SANS}", "--o-num-3": f"700 24px/1.2 {SANS}",
            "--o-num-4": f"700 20px/1.2 {SANS}",
            "--o-pad": "24px", "--o-gap": "16px", "--o-head-gap": "48px", "--o-side": "32px",
        },
        "changes": [
            "색: 페이지 바탕 `--bg` #F5F6F8 → #FFFFFF, 카드 면 `--surface` #FFFFFF → #F5F6F8(바탕과 면을 맞바꿈)",
            "글자 크기: KPI 숫자 40px → 48px(칸보다 넓으면 한 단계씩 줄여 한 줄 유지), 제목 28px → 32px",
            "간격: 머리 위 · KPI 위 여백 48px로 넉넉히, 카드 안쪽 24px · 테두리 1px 그대로",
        ],
        "use": "회의실 큰 화면이나 인쇄처럼 밝은 곳에서 숫자 네 개를 크게 보여 줄 때",
        "band": True, "cards": True,
    },
    {
        "key": "b", "label": "B", "name": "다크 금융 터미널",
        "vars": {
            "--o-bg": "#0E1621", "--o-card": "#152130", "--o-line": "#263547",
            "--o-text": "#E7EDF4", "--o-text-2": "#9DABBB",
            "--o-band-bg": "#0A1119", "--o-band-text": "#9DABBB",
            "--o-title": f"700 24px/1.3 {SANS}",
            "--o-num": f"700 32px/1.15 {SANS}", "--o-num-1": f"700 28px/1.15 {SANS}",
            "--o-num-2": f"700 24px/1.2 {SANS}", "--o-num-3": f"700 20px/1.2 {SANS}",
            "--o-num-4": f"700 18px/1.2 {SANS}",
            "--o-pad": "16px", "--o-gap": "8px", "--o-head-gap": "24px", "--o-side": "32px",
        },
        "changes": [
            "색: 바탕 #0E1621 · 면 #152130 · 구분선 #263547 · 글자 #E7EDF4 · 보조 #9DABBB(어두운 바탕용으로 새로)",
            "글자 크기: KPI 숫자 40px → 32px, 제목 28px → 24px(숫자를 촘촘히)",
            "간격: 카드 안쪽 24px → 16px, 카드 사이 16px → 8px",
        ],
        "use": "채권관리팀이 모니터에 띄워 두고 오래 들여다볼 때",
        "band": True, "cards": True,
    },
    {
        "key": "c", "label": "C", "name": "매거진 · 보고서형",
        "vars": {
            "--o-bg": "#FAF8F3", "--o-card": "#FAF8F3", "--o-line": "#CFCAC0",
            "--o-text": "#1B2026", "--o-text-2": "#5E5A52",
            "--o-band-bg": "#FAF8F3", "--o-band-text": "#5E5A52",
            "--o-title": f"700 44px/1.2 {SERIF}",
            "--o-num": f"700 56px/1.05 {SANS}", "--o-num-1": f"700 44px/1.1 {SANS}",
            "--o-num-2": f"700 32px/1.1 {SANS}", "--o-num-3": f"700 24px/1.2 {SANS}",
            "--o-num-4": f"700 20px/1.2 {SANS}",
            "--o-pad": "0px", "--o-gap": "32px", "--o-head-gap": "64px", "--o-side": "48px",
        },
        "changes": [
            "색: 바탕 #F5F6F8 → 종이색 #FAF8F3, 카드 면 · 테두리 없앰 → 가는 가로줄 #CFCAC0, 보조 글자 #5E5A52",
            "글자 크기: 제목 28px → 44px(Noto Serif KR, 제목에만), KPI 숫자 40px → 56px",
            "간격: 머리와 KPI 사이 48px → 64px, KPI는 카드 대신 위쪽 가는 줄 + 짧은 캡션",
        ],
        "use": "대표님께 드리는 월간 보고서 첫 장처럼 읽히게 할 때",
        "band": False, "cards": False,
    },
]


def contrast_rows(o):
    v = o["vars"]
    pairs = [("제목", v["--o-text"], v["--o-bg"]),
             ("KPI 숫자", v["--o-text"], v["--o-card"]),
             ("설명 · 라벨", v["--o-text-2"], v["--o-card"]),
             ("한 줄 소개", v["--o-text-2"], v["--o-bg"])]
    if o["band"]:
        pairs.append(("기준일 띠", v["--o-band-text"], v["--o-band-bg"]))
    return [(what, fg, bg, contrast(fg, bg)) for what, fg, bg in pairs]


def main():
    df = pd.read_csv(bp.SRC, encoding="utf-8-sig")
    s = bp.compute(df, bp.LINE0)
    n = len(df)
    over = df["overdue_usd"]
    kpis = [
        ("위험 바이어", f'{s["c_n"]}<span class="o-unit">곳</span>', f"C등급 · 위험 선 {bp.LINE0}% 이상"),
        ("C등급 채권", bp.money(s["c_ar"]), f'전체 채권의 {bp.pct(s["c_ar"] / s["total"])}'),
        ("전체 채권", bp.money(s["total"]), f"{n}곳"),
        ("연체 금액", bp.money(float(over.sum())), f"연체가 있는 곳 {int((over > 0).sum())}곳"),
    ]
    e = html.escape
    T = bp.TOKENS

    blocks, all_rows = [], []
    for o in OPTIONS:
        rows = contrast_rows(o)
        all_rows += [(o["label"],) + r for r in rows]
        css_vars = "; ".join(f"{k}: {val}" for k, val in o["vars"].items())
        band = (f'<p class="o-band">기준일 {bp.AS_OF} · 바이어 {n}곳 · 합성 데이터</p>' if o["band"]
                else f'<p class="o-dateline">{bp.AS_OF} 기준 · 바이어 {n}곳 · 합성 데이터</p>')
        kpi_html = "".join(
            f'<div class="o-kpi"><p class="o-label">{label}</p><p class="o-num">{num}</p>'
            f'<p class="o-note">{note}</p></div>' for label, num, note in kpis)
        crow = "".join(
            f'<tr><td>{what}</td><td class="num">{fg}</td><td class="num">{bg}</td>'
            f'<td class="num">{r:.2f} : 1</td><td>{"통과" if r >= 4.5 else "미달"}</td></tr>'
            for what, fg, bg, r in rows)
        blocks.append(f"""
  <section class="opt-wrap">
    <div class="opt-meta">
      <p class="opt-tag">{o["label"]}</p>
      <div>
        <h2>{o["label"]} · {e(o["name"])}</h2>
        <ul class="changes">{''.join(f'<li>{e(c)}</li>' for c in o["changes"])}</ul>
        <p class="use">어울리는 쓰임: {e(o["use"])}</p>
      </div>
    </div>
    <div class="opt opt-{o['key']}{' no-cards' if not o['cards'] else ''}" style="{css_vars}">
      {band}
      <div class="o-head">
        <h1 class="o-title">바이어 리스크 한눈에</h1>
        <p class="o-sub">(가상) 한빛정밀(주) 바이어 {n}곳 · 합성 데이터</p>
      </div>
      <div class="o-kpis">{kpi_html}</div>
    </div>
    <details class="ctr"><summary>대비 표 — {o["label"]}안 (가장 낮은 값 {min(r[3] for r in rows):.2f} : 1)</summary>
      <table><thead><tr><th>무엇</th><th class="num">글자</th><th class="num">바탕</th><th class="num">대비</th><th>4.5 : 1</th></tr></thead>
      <tbody>{crow}</tbody></table></details>
  </section>""")

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>머리 3안 비교 — 바이어 리스크 한눈에</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@700&display=swap" rel="stylesheet">
<style>
  :root {{ {"; ".join(f"{k}: {v}" for k, v in T.items())}; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: var(--bg); color: var(--text); }}
  body {{ font: var(--fs-body); word-break: keep-all; overflow-wrap: break-word; }}
  h1, h2, p, ul {{ margin: 0; }}
  .page {{ max-width: var(--page-max); margin: 0 auto; padding: var(--sp-7) var(--sp-7) var(--sp-8); }}
  .page-head h1 {{ font: var(--fs-title); color: var(--text); }}
  .page-head p {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-1); }}
  .num {{ font-variant-numeric: tabular-nums; white-space: nowrap; text-align: right; }}

  .opt-wrap {{ margin-top: var(--sp-7); }}
  .opt-meta {{ display: flex; gap: var(--sp-4); align-items: flex-start; margin-bottom: var(--sp-4); }}
  .opt-tag {{ font: var(--fs-display); color: var(--accent); min-width: var(--sp-7); }}
  .opt-meta h2 {{ font: var(--fs-section); color: var(--text); }}
  .changes {{ padding-left: var(--sp-5); margin-top: var(--sp-2); font: var(--fs-small); color: var(--text); }}
  .use {{ font: var(--fs-small); color: var(--text-2); margin-top: var(--sp-2); }}

  /* 안마다 바탕 · 글자색을 그 틀 안에서 다시 정한다 */
  .opt {{ background: var(--o-bg); color: var(--o-text); border: 1px solid var(--border); border-radius: var(--radius);
          overflow: hidden; padding-bottom: var(--o-head-gap); }}
  .o-band {{ background: var(--o-band-bg); color: var(--o-band-text); font: var(--fs-small); padding: var(--sp-2) var(--o-side); }}
  .o-dateline {{ color: var(--o-band-text); font: var(--fs-small); padding: var(--sp-6) var(--o-side) 0;
                 letter-spacing: 0.02em; }}
  .o-head {{ padding: var(--o-head-gap) var(--o-side) 0; }}
  .o-title {{ font: var(--o-title); color: var(--o-text); }}
  .o-sub {{ font: var(--fs-small); color: var(--o-text-2); margin-top: var(--sp-2); }}
  .o-kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--o-gap);
             padding: var(--o-head-gap) var(--o-side) 0; }}
  .o-kpi {{ background: var(--o-card); border: 1px solid var(--o-line); border-radius: var(--radius);
            padding: var(--o-pad); min-width: 0; }}
  .o-label {{ font: var(--fs-small); font-weight: 500; color: var(--o-text-2); }}
  .o-num {{ font: var(--o-num); color: var(--o-text); font-variant-numeric: tabular-nums; white-space: nowrap;
            overflow: hidden; margin-top: var(--sp-3); }}
  .o-num.f1 {{ font: var(--o-num-1); }} .o-num.f2 {{ font: var(--o-num-2); }} .o-num.f3 {{ font: var(--o-num-3); }} .o-num.f4 {{ font: var(--o-num-4); }}
  .o-unit {{ font: var(--fs-small); font-weight: 500; color: var(--o-text-2); margin-left: var(--sp-1); }}
  .o-note {{ font: var(--fs-small); color: var(--o-text-2); margin-top: var(--sp-2); }}

  /* B: 카드 테두리 대신 촘촘한 칸, 숫자 위주 */
  .opt-b .o-kpi {{ border-radius: var(--radius-sm); }}
  /* C: 카드 없이 위쪽 가는 줄 + 캡션 */
  .no-cards .o-kpi {{ background: transparent; border: 0; border-top: 1px solid var(--o-line); border-radius: 0;
                      padding: var(--sp-4) 0 0; }}
  .no-cards .o-head {{ border-bottom: 2px solid var(--o-text); padding-bottom: var(--sp-5); margin: 0 var(--o-side); padding-left: 0; padding-right: 0; }}

  .ctr {{ margin-top: var(--sp-3); font: var(--fs-small); color: var(--text-2); }}
  .ctr summary {{ cursor: pointer; color: var(--text); }}
  .ctr table {{ border-collapse: collapse; margin-top: var(--sp-2); width: 100%; max-width: 640px; }}
  .ctr th, .ctr td {{ padding: var(--sp-1) var(--sp-2); border-bottom: 1px solid var(--border); color: var(--text); text-align: left; }}
  .ctr th {{ color: var(--text-2); font-weight: 500; }}
  .ctr .num {{ text-align: right; }}

  @media (max-width: 760px) {{
    .page {{ padding: var(--sp-5) var(--sp-4) var(--sp-7); }}
    .opt {{ --o-side: var(--sp-3) !important; }}  /* 안마다 붙인 인라인 여백보다 휴대폰 여백이 이기게 */
    .o-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--sp-2); }}
    .opt-tag {{ font: var(--fs-title); color: var(--accent); min-width: var(--sp-6); }}
    .opt .o-kpi {{ padding: var(--sp-3); }}
    .no-cards .o-kpi {{ padding: var(--sp-3) 0 0; }}
  }}
</style>
</head>
<body>
<div class="page">
  <header class="page-head">
    <h1>머리 3안 비교</h1>
    <p>세 안의 숫자는 모두 같고(위험 선 {bp.LINE0}% 기준) 모양만 다릅니다. 하나를 고르시면 그 안으로 보드 전체(v2)를 바꿉니다.</p>
  </header>
{''.join(blocks)}
</div>
<script>
  // KPI 숫자가 칸보다 넓으면 그 안의 네 칸을 함께 한 단계씩 줄인다
  function fit() {{
    document.querySelectorAll('.opt').forEach(opt => {{
      const els = Array.from(opt.querySelectorAll('.o-num'));
      const steps = ['f1', 'f2', 'f3', 'f4'];
      els.forEach(el => el.classList.remove(...steps));
      for (const c of steps) {{
        if (els.every(el => el.scrollWidth <= el.clientWidth)) break;
        els.forEach(el => {{ el.classList.remove(...steps); el.classList.add(c); }});
      }}
    }});
  }}
  window.addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  fit();
</script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")

    print(f"위험 선 {bp.LINE0}% — C등급 {s['c_n']}곳 · C등급 채권 {bp.money(s['c_ar'])} · 전체 {bp.money(s['total'])}")
    for label, what, fg, bg, r in all_rows:
        print(f"  {label}안 {what:<8} {fg} on {bg}  {r:5.2f} {'OK' if r >= 4.5 else 'FAIL'}")
    low = min(all_rows, key=lambda x: x[4])
    print(f"  가장 낮은 값: {low[0]}안 {low[1]} {low[4]:.2f}")
    print(f"→ {OUT.relative_to(bp.ROOT).as_posix()} ({OUT.stat().st_size:,} 바이트)")


if __name__ == "__main__":
    main()
