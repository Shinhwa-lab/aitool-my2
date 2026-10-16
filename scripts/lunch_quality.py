"""3일차 실습 C — 한빛식당(가상) 점심 기록 진단. 안내서 「3. 데이터 진단」을 그대로 옮긴 스크립트.

실행: `uv run python scripts/lunch_quality.py`
입력(읽기만): labs/day3/lab-c/hanbit_lunch_log.csv (UTF-8 BOM)
출력: workbench/day3/outputs/lunch_quality.md

원본은 고치지 않는다. 날짜 해석(R1의 연도 규칙)은 범위 · 중복 · 요일 확인에만 쓰고 저장하지 않는다.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "labs/day3/lab-c/hanbit_lunch_log.csv"
OUT_DIR = ROOT / "workbench/day3/outputs"
OUT_MD = OUT_DIR / "lunch_quality.md"

WEEKDAY_KO = "월화수목금토일"
WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEATHER_OK = {"맑음", "흐림", "비", "눈"}
# 안내서 R9의 변형 이름 — 진단에서는 '섞였는지'만 센다
MENU_VARIANTS = {"돈까스": "돈가스", "카레라이스": "카레", "제육": "제육볶음",
                 "치킨마요덮밥": "치킨마요", "김치 찌개": "김치찌개"}
EVENT_VARIANTS = {"외부손님": "외부 손님 방문", "전사교육": "전사 교육"}

DATE_FORMATS = [
    ("YYYY-MM-DD", re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")),
    ("YYYY/MM/DD", re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")),
    ("YYYY.M.D", re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$")),
    ("M월 D일(연도 없음)", re.compile(r"^(\d{1,2})월 (\d{1,2})일$")),
]


def date_format(s):
    for name, pat in DATE_FORMATS:
        if pat.match(s):
            return name
    return "기타"


def parse_date(s):
    """R1과 같은 읽기 — 연도가 없으면 10–12월은 2025년, 1–9월은 2026년."""
    for name, pat in DATE_FORMATS:
        m = pat.match(s)
        if not m:
            continue
        if name.startswith("M월"):
            mon, day = int(m.group(1)), int(m.group(2))
            year = 2025 if mon >= 10 else 2026
        else:
            year, mon, day = (int(g) for g in m.groups())
        return pd.Timestamp(year=year, month=mon, day=day)
    return pd.NaT


def weekday_style(s):
    if len(s) == 1 and s in WEEKDAY_KO:
        return "한 글자(월)"
    if len(s) == 3 and s.endswith("요일") and s[0] in WEEKDAY_KO:
        return "'요일' 붙음(월요일)"
    if s in WEEKDAY_EN:
        return "영어(Mon)"
    return "기타"


def weekday_index(s):
    if s and s[0] in WEEKDAY_KO:
        return WEEKDAY_KO.index(s[0])
    if s in WEEKDAY_EN:
        return WEEKDAY_EN.index(s)
    return None


def to_num(s):
    try:
        return float(s)
    except ValueError:
        return None


def md_cell(s):
    return str(s).replace("|", "\\|")


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    raw_lines = SRC.read_text(encoding="utf-8-sig").splitlines()
    df["_line"] = range(2, len(df) + 2)  # 파일 기준 줄 번호(머리 줄 = 1)
    df["_raw"] = [raw_lines[i - 1] for i in df["_line"]]
    df["_date"] = df["날짜"].map(parse_date)

    holiday = df["비고"].eq("휴무")
    work = df[~holiday]  # 휴무 줄은 '휴무 줄'로만 세고 다른 검사에서는 뺀다

    def ex_cells(rows, col, n=2):
        """서로 다른 원본 값 n개를 줄 번호와 함께."""
        out, seen = [], set()
        for _, r in rows.iterrows():
            v = r[col]
            if v in seen:
                continue
            seen.add(v)
            out.append(f"`{md_cell(v) if v else '(빈칸)'}` ({r['_line']}줄)")
            if len(out) == n:
                break
        return " · ".join(out) if out else "-"

    def ex_rows(rows, n=2):
        return " · ".join(f"`{md_cell(r['_raw'])}` ({r['_line']}줄)" for _, r in rows.head(n).iterrows()) or "-"

    issues = []  # (종류, 줄 수, 예시, 덧붙임)

    # 1 날짜 형식 섞임
    fmt = df["날짜"].map(date_format)
    bad_date = df[fmt.ne("YYYY-MM-DD")]
    fmt_counts = fmt[fmt.ne("YYYY-MM-DD")].value_counts()
    issues.append(("날짜 형식 섞임", len(bad_date), ex_cells(bad_date, "날짜"),
                   " · ".join(f"{k} {v}" for k, v in fmt_counts.items())))

    # 2 요일 표기 섞임 (+ 적힌 요일이 실제와 다른 줄)
    wstyle = df["요일"].map(weekday_style)
    bad_wd = df[wstyle.ne("한 글자(월)")]
    style_counts = wstyle[wstyle.ne("한 글자(월)")].value_counts()
    widx = df["요일"].map(weekday_index)
    wd_wrong = df[widx.notna() & df["_date"].notna() & (widx != df["_date"].dt.weekday)]
    issues.append(("요일 표기 섞임", len(bad_wd), ex_cells(bad_wd, "요일"),
                   " · ".join(f"{k} {v}" for k, v in style_counts.items())))
    wrong_ex = " · ".join(
        f"`{md_cell(r['날짜'])}`에 `{md_cell(r['요일'])}` (실제 {WEEKDAY_KO[r['_date'].weekday()]}, {r['_line']}줄)"
        for _, r in wd_wrong.head(2).iterrows()) or "-"
    issues.append(("└ 적힌 요일이 실제 요일과 다름", len(wd_wrong), wrong_ex, "표기 섞임과 별도로 셈"))

    # 3 같은 날짜가 두 줄
    dup_mask = df["_date"].notna() & df["_date"].duplicated(keep=False)
    dup = df[dup_mask]
    exact_groups = recount_groups = 0
    for _, g in dup.groupby("_date"):
        if g["비고"].str.contains("재집계").any():
            recount_groups += 1
        elif (g.drop(columns=["_line", "_raw"]).nunique() <= 1).all():
            exact_groups += 1
    n_dup_dates = dup["_date"].nunique()
    issues.append(("같은 날짜가 두 줄", len(dup), ex_rows(dup),
                   f"날짜 {n_dup_dates}개 — 완전히 같은 줄 {exact_groups}쌍 · '재집계' 포함 {recount_groups}쌍"))

    # 4 휴무 줄
    hol = df[holiday]
    issues.append(("휴무 줄", len(hol), ex_rows(hol), "출근예정 · 식수 0, 나머지 빈칸"))

    # 5 식수 빈칸
    meal_blank = work[work["식수"].eq("")]
    issues.append(("식수 빈칸", len(meal_blank), ex_rows(meal_blank), ""))

    # 6 불가능해 보이는 식수
    att = work["출근예정"].map(to_num)
    meal = work["식수"].map(to_num)
    both = att.notna() & meal.notna()
    too_many = both & (meal > att)
    too_few = both & (meal < att * 0.2)
    impossible = work[too_many | too_few]
    issues.append(("불가능해 보이는 식수", len(impossible), ex_rows(impossible),
                   f"출근예정보다 많음 {int(too_many.sum())} · 출근예정의 20% 미만 {int(too_few.sum())}"))

    # 7 날씨 표기 섞임
    weather_blank = work[work["날씨"].eq("")]
    weather_bad = work[work["날씨"].ne("") & ~work["날씨"].isin(WEATHER_OK)]
    wv = weather_bad["날씨"].value_counts()
    issues.append(("날씨 표기 섞임", len(weather_bad), ex_cells(weather_bad, "날씨"),
                   " · ".join(f"`{k}` {v}" for k, v in wv.items())))
    issues.append(("└ 날씨 빈칸", len(weather_blank), ex_rows(weather_blank), "휴무 줄 제외"))

    # 8 최고기온의 단위와 빈칸
    t = work["최고기온"]
    t_c1 = work[t.str.contains("℃", regex=False)]
    t_c2 = work[t.str.contains("°C", regex=False)]
    t_blank = work[t.eq("")]
    t_stripped = t.str.replace("℃", "", regex=False).str.replace("°C", "", regex=False).str.strip()
    t_nonnum = work[t.ne("") & t_stripped.map(to_num).isna()]
    issues.append(("최고기온 단위 `℃`", len(t_c1), ex_cells(t_c1, "최고기온"), ""))
    issues.append(("최고기온 단위 `°C`", len(t_c2), ex_cells(t_c2, "최고기온"), "숫자와 단위 사이에 공백"
                   if t_c2["최고기온"].str.contains(" ", regex=False).all() and len(t_c2) else ""))
    issues.append(("최고기온 빈칸", len(t_blank), ex_rows(t_blank), "휴무 줄 제외"))
    if len(t_nonnum):
        issues.append(("최고기온 숫자로 안 읽힘", len(t_nonnum), ex_cells(t_nonnum, "최고기온"), ""))

    # 9 메뉴 · 행사 이름 섞임
    menu_bad = work[work["메인메뉴"].isin(MENU_VARIANTS)]
    event_bad = work[work["행사"].isin(EVENT_VARIANTS)]
    mv = menu_bad["메인메뉴"].value_counts()
    ev = event_bad["행사"].value_counts()
    issues.append(("메뉴 이름 섞임", len(menu_bad), ex_cells(menu_bad, "메인메뉴"),
                   " · ".join(f"`{k}` {v}" for k, v in mv.items())))
    issues.append(("행사 이름 섞임", len(event_bad), ex_cells(event_bad, "행사"),
                   " · ".join(f"`{k}` {v}" for k, v in ev.items())))

    # 10 출근예정 빈칸
    att_blank = work[work["출근예정"].eq("")]
    issues.append(("출근예정 빈칸", len(att_blank), ex_rows(att_blank), "휴무 줄 제외"))

    # 비고
    memo = df.loc[df["비고"].ne(""), "비고"].value_counts()

    # 사람이 정할 줄 = 불가능한 식수 + 식수 빈칸
    decide = []
    for _, r in impossible.iterrows():
        a, m = to_num(r["출근예정"]), to_num(r["식수"])
        why = "식수 > 출근예정" if m > a else f"식수가 출근예정의 {m / a * 100:.1f}%"
        if r["비고"] == "수기 집계":
            why += " — R6에서 '뺀다' / '×10 보정' 결정 필요"
        decide.append((r, why))
    for _, r in meal_blank.iterrows():
        decide.append((r, "식수 빈칸 — 규칙(R5)대로면 뺀다(지어내지 않는다)"))
    decide.sort(key=lambda x: x[0]["_line"])

    dates = df["_date"].dropna()
    lines = [
        "# 한빛식당(가상) 점심 기록 진단",
        "",
        f"- 원본: `{SRC.relative_to(ROOT).as_posix()}` (읽기만 함, 수정 없음)",
        f"- 만든 코드: `scripts/lunch_quality.py` — 숫자는 모두 이 코드가 센 값",
        "- 날짜 해석은 R1과 같은 규칙(연도 없으면 10–12월 → 2025년, 1–9월 → 2026년)으로, 범위 · 중복 · 요일 확인에만 썼다",
        "- 휴무 줄은 '휴무 줄'로만 세고, 다른 빈칸 · 불가능 검사에서는 뺐다",
        "",
        "## 1. 줄 수 · 열 이름 · 날짜 범위",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 줄 수(머리 줄 제외) | {len(df)} |",
        f"| 열 수 | {len(df.columns) - 3} |",
        f"| 열 이름 | {' · '.join(c for c in df.columns if not c.startswith('_'))} |",
        f"| 날짜 범위 | {dates.min():%Y-%m-%d} – {dates.max():%Y-%m-%d} |",
        f"| 해석 못 한 날짜 | {int(df['_date'].isna().sum())}줄 |",
        f"| 서로 다른 날짜 수 | {dates.nunique()} |",
        "",
        "## 2. 엉망인 곳 — 종류별",
        "",
        "줄 번호는 파일 기준(머리 줄 = 1줄)이다. 예시는 원본 글자 그대로다.",
        "",
        "| 종류 | 줄 수 | 예시 2개(원본 그대로) | 덧붙임 |",
        "|---|---:|---|---|",
    ]
    for kind, n, ex, note in issues:
        lines.append(f"| {kind} | {n} | {ex} | {note} |")
    lines += [
        "",
        "## 3. 비고 열에 나오는 글",
        "",
        "| 비고 | 줄 수 |",
        "|---|---:|",
    ]
    for k, v in memo.items():
        lines.append(f"| {md_cell(k)} | {v} |")
    lines.append(f"| (빈칸) | {int(df['비고'].eq('').sum())} |")
    lines += [
        "",
        "## 4. 사람이 정해야 할 줄",
        "",
        "| 줄 | 날짜 | 출근예정 | 식수 | 비고 | 왜 |",
        "|---:|---|---:|---:|---|---|",
    ]
    for r, why in decide:
        lines.append(f"| {r['_line']} | {md_cell(r['날짜'])} | {r['출근예정'] or '(빈칸)'} | "
                     f"{r['식수'] or '(빈칸)'} | {md_cell(r['비고']) or '(빈칸)'} | {why} |")
    lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"줄 수 {len(df)} · 날짜 범위 {dates.min():%Y-%m-%d} – {dates.max():%Y-%m-%d}")
    for kind, n, _, note in issues:
        print(f"  {kind}: {n}  {note}")
    print("비고:", dict(memo))
    print("사람이 정할 줄:")
    for r, why in decide:
        print(f"  {r['_line']}줄 {r['날짜']} 출근 {r['출근예정']} 식수 {r['식수']} 비고 {r['비고']} — {why}")
    print(f"→ {OUT_MD.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
