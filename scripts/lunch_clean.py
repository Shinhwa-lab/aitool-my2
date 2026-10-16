"""3일차 실습 C — 한빛식당(가상) 점심 기록 정제. `workbench/day3/outputs/lunch_rules.md`의 표를 그대로 옮긴 스크립트.

실행: `uv run python scripts/lunch_clean.py`
입력(읽기만): labs/day3/lab-c/hanbit_lunch_log.csv (UTF-8 BOM)
출력: workbench/day3/outputs/lunch_clean.csv (UTF-8 BOM) · workbench/day3/outputs/lunch_clean_log.md

적용 순서: R1 → R2 → R3 → R4 → R5 → R10 → R6 → R7 → R8 → R9 → 마무리.
줄 수는 그 규칙을 적용할 때 남아 있는 줄에서 센다.
"""
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "labs/day3/lab-c/hanbit_lunch_log.csv"
OUT_DIR = ROOT / "workbench/day3/outputs"
OUT_CSV = OUT_DIR / "lunch_clean.csv"
OUT_LOG = OUT_DIR / "lunch_clean_log.md"

COLS = ["날짜", "요일", "날씨", "최고기온", "메인메뉴", "행사", "월급날", "출근예정", "식수", "비고"]
WEEKDAY_KO = "월화수목금토일"
WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# R6 — 수강생 결정: "'수기 집계' 줄은 뺀다"
HANDWRITTEN_DECISION = "뺀다"  # "뺀다" 또는 "×10 보정"

WEATHER_MAP = {"맑": "맑음", "sunny": "맑음",
               "구름많음": "흐림", "cloudy": "흐림",
               "rain": "비", "우천": "비", "소나기": "비", "흐리고 비": "비",
               "snow": "눈", "": "모름"}
MENU_MAP = {"돈까스": "돈가스", "카레라이스": "카레", "제육": "제육볶음",
            "치킨마요덮밥": "치킨마요", "김치 찌개": "김치찌개"}
EVENT_MAP = {"외부손님": "외부 손님 방문", "전사교육": "전사 교육"}

DATE_PATTERNS = [
    re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"),
    re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$"),
    re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$"),
]
DATE_NO_YEAR = re.compile(r"^(\d{1,2})월 (\d{1,2})일$")


def r1_date(s):
    s = s.strip()
    for pat in DATE_PATTERNS:
        m = pat.match(s)
        if m:
            y, mo, d = (int(g) for g in m.groups())
            return f"{y:04d}-{mo:02d}-{d:02d}"
    m = DATE_NO_YEAR.match(s)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = 2025 if mo >= 10 else 2026
        return f"{y:04d}-{mo:02d}-{d:02d}"
    raise ValueError(f"R1: 읽을 수 없는 날짜 {s!r}")


def written_weekday(s):
    s = s.strip()
    if s and s[0] in WEEKDAY_KO:
        return WEEKDAY_KO.index(s[0])
    if s in WEEKDAY_EN:
        return WEEKDAY_EN.index(s)
    return None


def round_half_up(x):
    return int(math.floor(x + 0.5))


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df = df[COLS].copy()
    n_start = len(df)
    log = []  # (순서, 규칙, 고친/뺀 줄 수, 남은 줄 수, 내용)

    # 1 · R1 날짜
    new_date = df["날짜"].map(r1_date)
    n = int((new_date != df["날짜"]).sum())
    df["날짜"] = new_date
    log.append((1, "R1 날짜를 YYYY-MM-DD로", n, len(df), "형식을 바꾼 줄"))

    # 2 · R2 요일 다시 계산 (적힌 요일이 실제와 달랐던 줄만 센다)
    actual = pd.to_datetime(df["날짜"]).dt.weekday
    written = df["요일"].map(written_weekday)
    wrong = df[written != actual]
    n = len(wrong)
    wrong_note = ", ".join(f"{d} 적힌 `{w}` → {WEEKDAY_KO[a]}"
                           for d, w, a in zip(wrong["날짜"], wrong["요일"], actual[wrong.index]))
    df["요일"] = actual.map(lambda i: WEEKDAY_KO[i])
    log.append((2, "R2 요일을 날짜에서 다시 계산", n, len(df), f"적힌 요일이 실제와 달랐던 줄: {wrong_note}"))

    # 3 · R3 휴무 빼기
    mask = df["비고"].eq("휴무")
    n = int(mask.sum())
    df = df[~mask]
    log.append((3, "R3 휴무 줄 빼기", n, len(df), "뺀 줄"))

    # 4 · R4 같은 날짜 두 줄 — '재집계' 줄, 없으면 나중 줄을 남긴다
    keep_idx = []
    for _, g in df.groupby("날짜", sort=False):
        recount = g[g["비고"].str.contains("재집계")]
        keep_idx.append(recount.index[-1] if len(recount) else g.index[-1])
    before = len(df)
    dup_dates = df.loc[df["날짜"].duplicated(keep=False), "날짜"].unique()
    df = df.loc[sorted(keep_idx)]
    n = before - len(df)
    log.append((4, "R4 같은 날짜 두 줄 정리", n, len(df), f"뺀 줄 · 겹친 날짜: {', '.join(dup_dates)}"))

    # 5 · R5 식수 빈칸 빼기
    mask = df["식수"].str.strip().eq("")
    n = int(mask.sum())
    dropped = ", ".join(df.loc[mask, "날짜"])
    df = df[~mask]
    log.append((5, "R5 식수 빈칸 줄 빼기", n, len(df), f"뺀 줄: {dropped}"))

    # 6 · R10 출근예정 빈칸 — 같은 요일 바로 앞 기록 4개(출근예정 있는 줄)의 median, 반올림
    df = df.sort_values("날짜", kind="stable")
    has_att = df["출근예정"].str.strip().ne("")
    filled = []
    for idx in df.index[~has_att]:
        d, wd = df.at[idx, "날짜"], df.at[idx, "요일"]
        prev = df[has_att & (df["요일"] == wd) & (df["날짜"] < d)].tail(4)
        vals = prev["출근예정"].astype(int).tolist()
        if len(vals) < 4:
            raise ValueError(f"R10: {d} 앞의 같은 요일 기록이 4개보다 적다({len(vals)}개)")
        med = pd.Series(vals).median()
        v = round_half_up(med)
        df.at[idx, "출근예정"] = str(v)
        filled.append(f"{d}({wd}) ← {list(prev['날짜'])}의 {vals} → median {med:g} → {v}")
    log.append((6, "R10 출근예정 빈칸 채우기", len(filled), len(df), "채운 줄: " + " / ".join(filled)))

    # 7 · R6 불가능한 식수 — '수기 집계' 줄은 수강생 결정대로
    att = df["출근예정"].astype(float)
    meal = df["식수"].astype(float)
    hand = df["비고"].eq("수기 집계")
    impossible = (meal > att) | (meal < att * 0.2)
    notes = []
    if HANDWRITTEN_DECISION == "×10 보정":
        for idx in df.index[hand]:
            notes.append(f"{df.at[idx, '날짜']} 수기 집계 식수 {df.at[idx, '식수']} → ×10")
            df.at[idx, "식수"] = str(int(df.at[idx, "식수"]) * 10)
        drop = impossible & ~hand
        n_fixed = int(hand.sum())
    else:  # "뺀다"
        drop = impossible | hand
        n_fixed = 0
    for idx in df.index[drop]:
        why = "수기 집계 — 결정: 뺀다" if hand[idx] else ("식수 > 출근예정" if meal[idx] > att[idx] else "식수 < 출근예정의 20%")
        notes.append(f"{df.at[idx, '날짜']} 출근 {df.at[idx, '출근예정']} 식수 {df.at[idx, '식수']} ({why})")
    df = df[~drop]
    log.append((7, "R6 불가능한 식수 빼기('수기 집계' = 뺀다)", int(drop.sum()) + n_fixed, len(df), " / ".join(notes)))

    # 8 · R7 날씨 넷으로
    new_w = df["날씨"].str.strip().map(lambda s: WEATHER_MAP.get(s, s))
    n = int((new_w != df["날씨"]).sum())
    df["날씨"] = new_w
    left = sorted(set(df["날씨"]) - {"맑음", "흐림", "비", "눈", "모름"})
    log.append((8, "R7 날씨 통일", n, len(df), f"바꾼 줄 · 남은 값 {sorted(set(df['날씨']))}" + (f" · 규칙 밖 값 {left}" if left else "")))

    # 9 · R8 최고기온 숫자만
    new_t = (df["최고기온"].str.replace("℃", "", regex=False)
             .str.replace("°C", "", regex=False).str.replace(" ", "", regex=False).str.strip())
    n = int((new_t != df["최고기온"]).sum())
    bad = [t for t in new_t if t != "" and pd.to_numeric(t, errors="coerce") != pd.to_numeric(t, errors="coerce")]
    if bad:
        raise ValueError(f"R8: 숫자로 안 읽히는 최고기온 {bad}")
    df["최고기온"] = new_t
    n_blank_t = int(df["최고기온"].eq("").sum())
    log.append((9, "R8 최고기온 단위 떼기", n, len(df), f"바꾼 줄 · 빈칸으로 둔 줄 {n_blank_t}"))

    # 10 · R9 이름 통일 — 메뉴와 행사를 따로 세어 더한다
    n_menu = int(df["메인메뉴"].isin(MENU_MAP).sum())
    n_event = int(df["행사"].isin(EVENT_MAP).sum())
    df["메인메뉴"] = df["메인메뉴"].map(lambda s: MENU_MAP.get(s, s))
    df["행사"] = df["행사"].map(lambda s: EVENT_MAP.get(s, s))
    log.append((10, "R9 메뉴 · 행사 이름 통일", n_menu + n_event, len(df), f"메뉴 {n_menu} + 행사 {n_event}"))

    # 마무리 — 월급날 0/1, 정수, 날짜순, 원본과 같은 10개 열
    df["월급날"] = df["월급날"].str.strip().map({"Y": 1, "": 0})
    if df["월급날"].isna().any():
        raise ValueError("월급날에 Y · 빈칸 말고 다른 값이 있다")
    df["출근예정"] = df["출근예정"].astype(int)
    df["식수"] = df["식수"].astype(int)
    df = df.sort_values("날짜").reset_index(drop=True)[COLS]
    if df["날짜"].duplicated().any():
        raise ValueError("정제 뒤에도 같은 날짜가 남았다")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    lines = [
        "# 한빛식당(가상) 점심 기록 정제 로그",
        "",
        "- 규칙: `workbench/day3/outputs/lunch_rules.md` · 코드: `scripts/lunch_clean.py`",
        f"- 원본 `{SRC.relative_to(ROOT).as_posix()}` (읽기만 함)",
        f"- 처음 {n_start}줄 → 남은 {len(df)}줄 · 날짜 {df['날짜'].min()} – {df['날짜'].max()}",
        "- 세는 법: 그 규칙을 적용할 때 남아 있는 줄에서 센다. R2는 적힌 요일이 실제와 달랐던 줄만, R9는 메뉴와 행사를 따로 세어 더한다.",
        f"- '수기 집계' 줄: {HANDWRITTEN_DECISION} (수강생 결정)",
        "",
        "| 순서 | 규칙 | 고친(뺀) 줄 수 | 남은 줄 수 | 내용 |",
        "|---:|---|---:|---:|---|",
    ]
    for order, rule, cnt, remain, note in log:
        lines.append(f"| {order} | {rule} | {cnt} | {remain} | {note.replace('|', '/')} |")
    lines.append("")
    OUT_LOG.write_text("\n".join(lines), encoding="utf-8")

    print(f"처음 {n_start}줄 → 남은 {len(df)}줄")
    for order, rule, cnt, remain, note in log:
        print(f"  {order:>2}. {rule}: {cnt} (남은 {remain}) — {note}")
    print(f"→ {OUT_CSV.relative_to(ROOT).as_posix()} · {OUT_LOG.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
