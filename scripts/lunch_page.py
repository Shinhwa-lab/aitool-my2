"""3일차 실습 C — 한빛식당(가상) 밥 예보 페이지. 깨끗한 표로 계산해 HTML 한 장을 쓴다.

실행: `uv run python scripts/lunch_page.py`
입력(읽기만): workbench/day3/outputs/lunch_clean.csv · labs/day3/lab-c/nutritionist_memo.md
출력: workbench/day3/outputs/hanbit_lunch.html

지금 구역(위에서부터): 머리 · 예보 성적표(「7. 예보관 시험」) · 영양사님 감 검증(「5. 감 검증」). 페이지 규칙은 안내서 「6」.
같은 입력이면 같은 페이지 — 날짜 · 시각을 넣지 않고, 난수는 고정한다.
"""
import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "workbench/day3/outputs/lunch_clean.csv"
MEMO = ROOT / "labs/day3/lab-c/nutritionist_memo.md"
PLAN = ROOT / "labs/day3/lab-c/next_week_plan.csv"
OUT = ROOT / "workbench/day3/outputs/hanbit_lunch.html"

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"
GAP = 2.0  # 100명당 2명 이상 차이 나면 '차이 있음' — 사람이 정한 선

# 「7. 예보관 시험」
TEST_START = "2026-09-14"  # 이 날 전 = 배우는 기간, 이 날부터 = 시험 기간
SPARE = 10  # AI 준비 = 예보 + 10
COST = 4500  # 1인분 원가(가정)
MENU_MULT = {"돈가스": 1.1, "카레": 1.1, "샐러드": 0.9}  # 나머지 1.0
TEXT_COLS = ["요일", "날씨", "메인메뉴", "행사"]
FEATURE_COLS = ["요일", "날씨", "최고기온", "메인메뉴", "행사", "월급날", "출근예정"]
MARKED_DAYS = {"2026-09-23": "추석 연휴 전날 · 돈가스", "2026-09-30": "비 오는 수요일 · 카레"}


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
        if len(c["groups"]) == 2:  # 코멘트에 쓸 차이(반올림 전 값으로)
            c["diff"] = round(abs(c["groups"][0]["raw"] - c["groups"][1]["raw"]), 1)
        for g in c["groups"]:
            g.pop("raw")
    return cards, len(base)


def make_features(rows, temp_fill, columns=None):
    """재료 — 최고기온 빈칸은 배우는 기간의 가운데 값, 행사 빈칸은 '없음', 글자 열은 get_dummies(drop_first 없이).
    시험 · 예보 때는 배울 때와 같은 열로 맞추고, 없는 열은 0."""
    X = rows[FEATURE_COLS].copy()
    X["최고기온"] = X["최고기온"].fillna(temp_fill)
    X["행사"] = X["행사"].fillna("없음")
    X = pd.get_dummies(X, columns=TEXT_COLS).astype(float)
    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0.0)
    return X


def nutritionist_formula(df, date, weekday, menu):
    """영양사님 공식 — 그날 전 같은 요일의 실제 식수 4개(가장 가까운 날부터) 평균 × 메뉴 배수."""
    prev = df[(df["날짜"] < date) & (df["요일"] == weekday)].tail(4)
    if len(prev) < 4:
        raise ValueError(f"공식: {date} 앞의 같은 요일 기록이 4개보다 적다")
    return float(prev["식수"].mean()) * MENU_MULT.get(menu, 1.0)


def forecast_test(df):
    train = df[df["날짜"] < TEST_START]
    test = df[df["날짜"] >= TEST_START]
    temp_fill = float(train["최고기온"].median())
    X_train = make_features(train, temp_fill)
    columns = list(X_train.columns)
    X_test = make_features(test, temp_fill, columns)
    y_train, y_test = train["식수"].to_numpy(float), test["식수"].to_numpy(float)

    models = {
        "선형 회귀": LinearRegression(),
        "LightGBM": LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15,
                                  min_child_samples=5, random_state=42, verbose=-1),
    }
    preds, scores = {}, {}
    for name, model in models.items():
        model.fit(X_train.to_numpy(), y_train)
        preds[name] = model.predict(X_test.to_numpy())
        scores[name] = float(np.mean(np.abs(preds[name] - y_test)))  # 하루 평균 몇 인분 차이
    chosen = min(scores, key=scores.get)  # 같으면 앞의 것(선형 회귀)

    days = []
    for (_, r), ai in zip(test.iterrows(), preds[chosen]):
        f = nutritionist_formula(df, r["날짜"], r["요일"], r["메인메뉴"])
        ai_prep = float(ai) + SPARE
        actual = int(r["식수"])
        days.append({
            "date": r["날짜"], "label": f"{int(r['날짜'][5:7])}/{int(r['날짜'][8:10])}({r['요일']})",
            "actual": actual, "ai": float(ai), "formula": f,
            "ai_left": max(ai_prep - actual, 0.0), "ai_short": max(actual - ai_prep, 0.0),
            "f_left": max(f - actual, 0.0), "f_short": max(actual - f, 0.0),
            "mark": MARKED_DAYS.get(r["날짜"]),
        })

    def total(key):
        return float(sum(d[key] for d in days))

    summary = {
        "ai": {"mae": scores[chosen], "left": total("ai_left"), "short": total("ai_short"),
               "short_days": sum(d["ai_short"] > 0 for d in days)},
        "formula": {"mae": float(np.mean([abs(d["formula"] - d["actual"]) for d in days])),
                    "left": total("f_left"), "short": total("f_short"),
                    "short_days": sum(d["f_short"] > 0 for d in days)},
    }
    for s in summary.values():
        s["left_won"] = s["left"] * COST
    return {
        "scores": scores, "chosen": chosen, "days": days, "summary": summary,
        "model": models[chosen], "columns": columns, "temp_fill": temp_fill,
        "train_range": (train["날짜"].min(), train["날짜"].max(), len(train)),
        "test_range": (test["날짜"].min(), test["날짜"].max(), len(test)),
    }


def round_half_up(x):
    return int(np.floor(x + 0.5))


def josa(word, pair):
    """받침에 맞는 조사 — pair: '이/가' · '은/는' · '으로/로'."""
    c = word[-1]
    jong = (ord(c) - 0xAC00) % 28 if "가" <= c <= "힣" else 0
    with_b, without_b = pair.split("/")
    if pair == "으로/로":
        return word + (with_b if jong not in (0, 8) else without_b)
    return word + (with_b if jong else without_b)


def next_week(df, fc, cards):
    """「8. 다음 주 예보」 — 다음 주 계획을 배울 때와 같은 열로 바꿔 우리 예보관에게 묻는다."""
    plan = pd.read_csv(PLAN, encoding="utf-8-sig", dtype={"월급날": str, "행사": str})
    plan = plan.rename(columns={"날씨예보": "날씨", "최고기온예보": "최고기온"})
    plan["월급날"] = plan["월급날"].fillna("").str.strip().map({"Y": 1, "": 0})
    X = make_features(plan, fc["temp_fill"], fc["columns"])
    preds = fc["model"].predict(X.to_numpy())

    belief = {c["no"]: c for c in cards}
    menu_rank = [g["label"] for g in belief[3]["groups"]]
    days = []
    for (_, r), p in zip(plan.iterrows(), preds):
        f = nutritionist_formula(df, r["날짜"], r["요일"], r["메인메뉴"])
        fcast, f_round = round_half_up(p), round_half_up(f)
        event = r["행사"] if isinstance(r["행사"], str) and r["행사"].strip() else ""
        days.append({"date": r["날짜"], "weekday": r["요일"], "weather": r["날씨"], "temp": r["최고기온"],
                     "menu": r["메인메뉴"], "event": event, "payday": int(r["월급날"]),
                     "attend": int(r["출근예정"]), "raw": float(p), "forecast": fcast,
                     "prep": fcast + SPARE, "formula": f_round})

    # 코멘트 — 그날 조건(감 검증에서 확인한 숫자) + 영양사님 공식과의 차이
    for d in days:
        why = []
        if d["payday"]:
            why.append(f"월급날은 보통 날보다 100명당 {belief[None]['diff']:.1f}명 적게 오셨어요")
        if d["weather"] == "비":
            why.append(f"비 오는 날은 맑은 날보다 100명당 {belief[1]['diff']:.1f}명 더 오셨어요")
        if d["weekday"] == "금":
            why.append(f"금요일은 월–목보다 100명당 {belief[2]['diff']:.1f}명 적었어요")
        if d["event"]:
            why.append(f"{josa(d['event'], '이/가')} 있는 날이고 출근예정은 {d['attend']}명이에요")
        if d["menu"] in menu_rank and menu_rank.index(d["menu"]) == len(menu_rank) - 1:
            why.append(f"{josa(d['menu'], '은/는')} 메뉴 중 가장 적게 오신 메뉴였어요")
        elif d["menu"] in menu_rank and menu_rank.index(d["menu"]) == 0:
            why.append(f"{josa(d['menu'], '은/는')} 메뉴 중 가장 많이 오신 메뉴였어요")
        if not why:
            why.append(f"{d['weekday']}요일 · {d['weather']} · {josa(d['menu'], '으로/로')} 특별한 조건이 없는 날이에요")
        gap = d["forecast"] - d["formula"]
        if gap == 0:
            tail = f"영양사님 공식({d['formula']}인분)과 같게 봤어요."
        else:
            tail = f"영양사님 공식({d['formula']}인분)보다 {abs(gap)}명 {'많게' if gap > 0 else '적게'} 봤어요."
        d["comment"] = "영양사님, " + " · ".join(why) + ". " + tail

    hi = max(days, key=lambda d: d["raw"])
    lo = min(days, key=lambda d: d["raw"])
    for d in days:
        d["tag"] = "이번 주 가장 많은 날" if d is hi else ("이번 주 가장 적은 날" if d is lo else "")
    return days


def render_next_week(days, chosen):
    e = html.escape
    cards = []
    for d in days:
        chips = [d["weather"], d["menu"]] + ([d["event"]] if d["event"] else []) + (["월급날"] if d["payday"] else [])
        cls = " hi" if d["tag"].endswith("많은 날") else (" lo" if d["tag"] else "")
        tag = (f'<span class="flag">{e(d["tag"])}</span>' if d["tag"]
               else '<span class="flag blank" aria-hidden="true">-</span>')
        cards.append(f"""
      <article class="card day{cls}">
        {tag}
        <div class="day-date">{int(d['date'][5:7])}/{int(d['date'][8:10])} <b>{e(d['weekday'])}요일</b></div>
        <div class="day-num">{d['forecast']}<small>명</small></div>
        <div class="day-prep">준비 {d['prep']}인분</div>
        <div class="day-formula">영양사님 공식이면 {d['formula']}인분</div>
        <div class="chips">{''.join(f'<span class="chip">{e(c)}</span>' for c in chips)}</div>
        <p class="comment">{e(d['comment'])}</p>
      </article>""")
    first, last = days[0]["date"], days[-1]["date"]
    return f"""
  <section id="next-week">
    <h2>다음 주 예보</h2>
    <p class="lead">{first} – {last}. 우리 예보관({e(chosen)})의 예보를 반올림했고, 준비 인분 = 예보 + {SPARE}인분입니다.
      작은 글씨는 견주어 보시라고 넣은 영양사님 공식(그날 전 같은 요일 4번의 평균 × 메뉴 배수)입니다. 준비량은 영양사님이 정해 주세요.</p>
    <div class="week">{''.join(cards)}
    </div>
  </section>"""


def render_forecast(fc):
    e = html.escape
    s_ai, s_f = fc["summary"]["ai"], fc["summary"]["formula"]
    t0, t1, tn = fc["train_range"]
    s0, s1, sn = fc["test_range"]

    model_rows = []
    for name, score in fc["scores"].items():
        picked = name == fc["chosen"]
        model_rows.append(
            f'<div class="model{" picked" if picked else ""}"><span class="k">{e(name)}</span>'
            f'<span class="v">{score:.1f}<small>인분</small></span>'
            f'<span class="d">{"우리 예보관으로 고름" if picked else "시험에서 짐"}</span></div>')

    marks = []
    for d in fc["days"]:
        if d["mark"]:
            marks.append(f'<li><b>{e(d["label"])} {e(d["mark"])}</b> — 실제 {d["actual"]}명 · '
                         f'AI 예보 {d["ai"]:.0f}명 · 영양사님 공식 {d["formula"]:.0f}인분</li>')

    def pair(title, ai_main, ai_sub, f_main, f_sub):
        return (f'<article class="card stat"><h3>{title}</h3><div class="nums">'
                f'<div><span class="k">AI(우리 예보관)</span><span class="v">{ai_main}</span>'
                f'<span class="d">{ai_sub}</span></div>'
                f'<div><span class="k">영양사님 공식</span><span class="v muted">{f_main}</span>'
                f'<span class="d">{f_sub}</span></div></div></article>')

    stats = "".join([
        pair("하루 평균 몇 인분 차이", f'{s_ai["mae"]:.1f}<small>인분</small>', "예보와 실제의 차이",
             f'{s_f["mae"]:.1f}<small>인분</small>', "공식과 실제의 차이"),
        pair("남은 밥(20일 합계)", f'{s_ai["left"]:.1f}<small>인분</small>', f'{s_ai["left_won"]:,.0f}원',
             f'{s_f["left"]:.1f}<small>인분</small>', f'{s_f["left_won"]:,.0f}원'),
        pair("모자란 밥(컵라면을 드신 분)", f'{s_ai["short"]:.1f}<small>인분</small>', f'모자란 날 {s_ai["short_days"]}일',
             f'{s_f["short"]:.1f}<small>인분</small>', f'모자란 날 {s_f["short_days"]}일'),
    ])

    return f"""
  <section id="forecast-test">
    <h2>예보 성적표</h2>
    <p class="lead">{t0} – {t1}({tn}일)의 기록으로 배우고, 배울 때 쓰지 않은 {s0} – {s1}({sn}일)로 시험했습니다.
      성적은 하루 평균 몇 인분 차이(많든 적든 크기만)이며 작을수록 좋습니다.</p>
    <div class="grid two">
      <article class="card">
        <h3>예보관 두 명의 시험 성적</h3>
        <div class="models">{''.join(model_rows)}</div>
        <p class="note"><b>복잡한 쪽이 늘 이기지는 않는다 — 시험으로 고른다.</b></p>
        <p class="note small">설정은 모두 같은 결과를 보려고 고정했습니다.</p>
      </article>
      <article class="card wide">
        <h3>시험 20일 — 실제 · 우리 예보관 · 영양사님 공식</h3>
        <div class="chart" style="height:280px"><canvas id="testChart" aria-label="시험 20일 선 그래프"></canvas></div>
        <ul class="marks">{''.join(marks)}</ul>
      </article>
    </div>
    <p class="lead" style="margin-top:16px">AI 준비 = 우리 예보관의 예보 + {SPARE}인분, 영양사님 준비 = 공식. 남은 밥은 1인분 {COST:,}원(가정)으로 셈했습니다.</p>
    <div class="grid three">{stats}</div>
  </section>"""


def render(df, cards, n_base, fc, week):
    start, end = df["날짜"].min(), df["날짜"].max()
    data = {"cards": cards,
            "test": {"chosen": fc["chosen"],
                     "labels": [d["label"] for d in fc["days"]],
                     "actual": [d["actual"] for d in fc["days"]],
                     "ai": [round(d["ai"], 1) for d in fc["days"]],
                     "formula": [round(d["formula"], 1) for d in fc["days"]],
                     "marks": [i for i, d in enumerate(fc["days"]) if d["mark"]]}}
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
  .grid.two {{ grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); }}
  .grid.three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  @media (max-width: 760px) {{ .grid.two, .grid.three {{ grid-template-columns: minmax(0, 1fr); }} }}
  .models {{ display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }}
  .model {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; padding: 10px 12px;
            border: 1px solid var(--line); border-radius: 10px; }}
  .model .k {{ flex: 1 0 100%; }}
  .model.picked {{ border-color: var(--accent); background: var(--accent-soft); }}
  .model.picked .d {{ color: var(--accent); font-weight: 700; }}
  .note.small {{ color: var(--ink-2); font-size: 14px; margin-top: 4px; }}
  .stat h3 {{ margin: 0 0 12px; }}
  .marks {{ margin: 12px 0 0; padding-left: 18px; font-size: 15px; }}
  .marks li + li {{ margin-top: 4px; }}
  .week {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }}
  @media (max-width: 900px) {{ .week {{ grid-template-columns: minmax(0, 1fr); }} }}
  .day {{ position: relative; padding: 16px 14px; }}
  .day.hi {{ border: 2px solid var(--accent); }}
  .day.lo {{ border: 2px dashed var(--gray); }}
  .flag {{ align-self: flex-start; font-size: 14px; font-weight: 700; padding: 1px 10px; border-radius: 999px;
           margin-bottom: 8px; }}
  .flag.blank {{ visibility: hidden; }}
  @media (max-width: 900px) {{ .flag.blank {{ display: none; }} }}
  .day.hi .flag {{ background: var(--accent); color: #fff; }}
  .day.lo .flag {{ background: var(--gray-soft); color: var(--ink-2); border: 1px solid var(--gray); }}
  .day-date {{ font-size: 15px; color: var(--ink-2); }}
  .day-date b {{ color: var(--ink); }}
  .day-num {{ font-size: 40px; font-weight: 700; line-height: 1.2; margin-top: 4px; font-variant-numeric: tabular-nums; }}
  .day-num small {{ font-size: 18px; font-weight: 500; margin-left: 2px; }}
  .day-prep {{ font-size: 17px; font-weight: 700; color: var(--accent); }}
  .day-formula {{ font-size: 14px; color: var(--ink-2); }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 0; }}
  .chip {{ font-size: 14px; padding: 1px 9px; border-radius: 6px; background: var(--gray-soft); color: var(--ink); }}
  .comment {{ margin: 10px 0 0; font-size: 14px; line-height: 1.55; color: var(--ink); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>한빛식당 밥 예보</h1>
    <p>(가상) 한빛정밀(주) 본사 구내식당 · 기록 기간 <span class="nw">{start} – {end}</span> · 만든 사람 총무팀 최 대리(가상)</p>
  </header>
{render_next_week(week, fc["chosen"])}
{render_forecast(fc)}

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
  const INK = css.getPropertyValue('--ink').trim();
  const WARN = css.getPropertyValue('--warn').trim();
  if (window.Chart) {{
    Chart.defaults.font.family = "'Noto Sans KR', sans-serif";
    Chart.defaults.font.size = 14;
    Chart.defaults.color = INK2;

    // 예보 성적표 — 시험 20일 선 그래프, 9/23 · 9/30에 세로 점선 표시
    const T = DATA.test;
    const markLines = {{
      id: 'markLines',
      afterDatasetsDraw(chart) {{
        const {{ ctx, chartArea, scales }} = chart;
        ctx.save();
        T.marks.forEach(i => {{
          const x = scales.x.getPixelForValue(i);
          ctx.strokeStyle = WARN; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
          ctx.beginPath(); ctx.moveTo(x, chartArea.top); ctx.lineTo(x, chartArea.bottom); ctx.stroke();
          ctx.setLineDash([]); ctx.fillStyle = WARN; ctx.font = "700 14px 'Noto Sans KR', sans-serif";
          ctx.textAlign = x > chartArea.right - 40 ? 'right' : 'center';
          ctx.fillText(T.labels[i].split('(')[0], x, chartArea.top - 6);
        }});
        ctx.restore();
      }}
    }};
    new Chart(document.getElementById('testChart'), {{
      type: 'line',
      data: {{
        labels: T.labels,
        datasets: [
          {{ label: '실제', data: T.actual, borderColor: INK, backgroundColor: INK, borderWidth: 2,
             pointRadius: T.labels.map((_, i) => T.marks.includes(i) ? 5 : 2), tension: 0 }},
          {{ label: '우리 예보관(' + T.chosen + ')', data: T.ai, borderColor: ACCENT, backgroundColor: ACCENT,
             borderWidth: 2, pointRadius: 2, tension: 0 }},
          {{ label: '영양사님 공식', data: T.formula, borderColor: GRAY, backgroundColor: GRAY,
             borderWidth: 2, borderDash: [6, 4], pointRadius: 2, tension: 0 }}
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false, animation: false,
        layout: {{ padding: {{ top: 22 }} }},
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ boxWidth: 14, boxHeight: 2 }} }},
          tooltip: {{ callbacks: {{ label: ctx => ' ' + ctx.dataset.label + ' ' + Math.round(ctx.parsed.y) + (ctx.datasetIndex === 2 ? '인분' : '명') }} }}
        }},
        scales: {{
          x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 0, autoSkip: true, autoSkipPadding: 10 }} }},
          y: {{ grid: {{ color: '#eef0f2' }}, title: {{ display: true, text: '식수(명)' }} }}
        }}
      }},
      plugins: [markLines]
    }});

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
    fc = forecast_test(df)
    week = next_week(df, fc, cards)
    OUT.write_text(render(df, cards, n_base, fc, week), encoding="utf-8")

    print(f"[다음 주 예보] 우리 예보관 = {fc['chosen']}")
    for d in week:
        print(f"  {d['date']}({d['weekday']}) {d['menu']} · {d['weather']} · {d['event'] or '-'} · 월급날 {d['payday']}: "
              f"예보 {d['raw']:.2f} → {d['forecast']}명 · 준비 {d['prep']}인분 · 공식 {d['formula']}인분 {d['tag']}")
        print(f"     {d['comment']}")
    sections = re.findall(r'<section id="([^"]+)"', render(df, cards, n_base, fc, week))
    print("  구역 순서:", " → ".join(["머리"] + sections))

    t0, t1, tn = fc["train_range"]
    s0, s1, sn = fc["test_range"]
    print(f"[예보 성적표] 배우는 기간 {t0} – {t1} ({tn}일) · 시험 기간 {s0} – {s1} ({sn}일)")
    for name, score in fc["scores"].items():
        print(f"  {name}: 하루 평균 {score:.2f}인분 차이" + (" ← 우리 예보관" if name == fc["chosen"] else ""))
    for d in fc["days"]:
        if d["mark"]:
            print(f"  {d['date']} {d['mark']}: 실제 {d['actual']} · AI 예보 {d['ai']:.1f} (준비 {d['ai'] + SPARE:.1f}) · 공식 {d['formula']:.1f}")
    for who, s in (("AI", fc["summary"]["ai"]), ("공식", fc["summary"]["formula"])):
        print(f"  {who}: 평균 차이 {s['mae']:.2f} · 남은 밥 {s['left']:.1f}인분 {s['left_won']:,.0f}원 · "
              f"모자란 밥 {s['short']:.1f}인분 · 모자란 날 {s['short_days']}일")
    print("[영양사님 감 검증]")

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
