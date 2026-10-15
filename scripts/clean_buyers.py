"""2일차 바이어 정제 — `workbench/day2/rules/정제규칙.md` 1–7칸을 그대로 옮긴 스크립트.

실행: `uv run python scripts/clean_buyers.py`
입력(읽기만): data/checkpoints/d2_start.xlsx (buyers · fx_at_ref) · data/checkpoints/fx_krw_daily.csv
출력: workbench/day2/outputs/d2_buyers_clean.csv · workbench/day2/outputs/dq_report.md
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC_XLSX = ROOT / "data/checkpoints/d2_start.xlsx"
SRC_FX_DAILY = ROOT / "data/checkpoints/fx_krw_daily.csv"
OUT_DIR = ROOT / "workbench/day2/outputs"
OUT_CSV = OUT_DIR / "d2_buyers_clean.csv"
OUT_REPORT = OUT_DIR / "dq_report.md"

AS_OF = pd.Timestamp("2026-08-31")
AR_COLS = ["ar_balance", "ar_current", "ar_1_30", "ar_31_60", "ar_61_90", "ar_91p"]
BUCKETS = AR_COLS[1:]
FIN_FLAG_COLS = ["current_assets", "current_liabilities", "total_liabilities", "equity", "revenue"]
RATIO_COLS = ["current_ratio", "debt_to_equity", "dso_buyer", "op_margin"]

# 1칸 — map_ccy 시트가 비어 있어 매핑표를 여기에 둔다(규칙 문서 1칸과 같은 내용)
MAP_CCY = {"USD": "USD", "US$": "USD", "usd": "USD", "EUR": "EUR", "euro": "EUR",
           "JPY": "JPY", "yen": "JPY", "CNY": "CNY", "RMB": "CNY"}
FX_DAILY_COL = {"USD": "usd_krw", "EUR": "eur_krw", "CNY": "cny_krw", "JPY": "jpy100_krw"}
FX_AT_REF_CCY = {"USD": "USD", "EUR": "EUR", "CNY": "CNY", "JPY": "JPY100"}


def to_number(v):
    """2칸 — 앞뒤 공백 · 콤마 · 통화 글자를 지우고, 끝의 k는 ×1000."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    scale = 1000 if s.endswith("k") else 1
    s = re.sub(r"[a-z$,\s]", "", s)
    return float(s) * scale if s else np.nan


def is_text(v):
    return isinstance(v, str)


def md_table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def main():
    raw = pd.read_excel(SRC_XLSX, sheet_name="buyers", dtype=object)
    fx_ref = pd.read_excel(SRC_XLSX, sheet_name="fx_at_ref")
    fx_daily = pd.read_csv(SRC_FX_DAILY, parse_dates=["date"])
    df = raw.copy()

    # 1칸 통화
    df["ccy"] = df["currency"].map(MAP_CCY)
    if df["ccy"].isna().any():
        raise ValueError(f"매핑되지 않은 통화: {sorted(df.loc[df['ccy'].isna(), 'currency'].unique())}")

    # 2칸 숫자 변환
    for c in AR_COLS:
        df[f"{c}_num"] = df[c].map(to_number)

    # 7칸 환율 — 기준일 2026-08-31 행만 쓴다(9-30 행은 쓰지 않음)
    ref = fx_ref[fx_ref["ref_date"] == AS_OF].set_index("ccy")
    usd_krw = ref.loc["USD", "krw_close"]

    def krw_per_unit(ccy):
        rate = ref.loc[FX_AT_REF_CCY[ccy], "krw_close"]
        return rate / 100 if ccy == "JPY" else rate  # 엔화는 100엔 단위

    df["to_usd"] = df["ccy"].map(lambda c: krw_per_unit(c) / usd_krw)

    # 4칸 단위 의심 — USD 환산 잔액 > 한도 × 10 이면 플래그 후 ÷1,000
    usd_before = df["ar_balance_num"] * df["to_usd"]
    df["unit_flag"] = (usd_before > df["credit_limit_usd"].astype(float) * 10).astype(int)
    df.loc[df["unit_flag"] == 1, "ar_balance_num"] = df["ar_balance_num"] / 1000
    df["ar_balance_usd"] = (df["ar_balance_num"] * df["to_usd"]).round(2)

    # 2칸 — 다섯 구간 합과 잔액이 다르면 표시
    bucket_sum = df[[f"{c}_num" for c in BUCKETS]].sum(axis=1)
    df["amt_check"] = ((bucket_sum - df["ar_balance_num"]).abs() > 0.5).astype(int)

    # 5칸 자본잠식 · 3칸 비율 계산
    fin = df[["current_assets", "current_liabilities", "total_liabilities", "equity",
              "accounts_receivable", "revenue", "operating_income"]].astype(float)
    df["neg_equity"] = (fin["equity"] <= 0).astype(int)
    df["current_ratio"] = fin["current_assets"] / fin["current_liabilities"]
    df["debt_to_equity"] = (fin["total_liabilities"] / fin["equity"]).where(df["neg_equity"] == 0)
    df["dso_buyer"] = fin["accounts_receivable"] / fin["revenue"] * 365
    df["op_margin"] = fin["operating_income"] / fin["revenue"]

    # 3칸 결측 — 플래그, 그리고 비율 열을 대체 전 중위수로 채움(자본잠식 빈칸은 그대로)
    df["fin_missing"] = fin[FIN_FLAG_COLS].isna().any(axis=1).astype(int)
    ratio_before = df[RATIO_COLS].copy()
    medians = ratio_before.median()
    for c in RATIO_COLS:
        fill_mask = df[c].isna()
        if c == "debt_to_equity":
            fill_mask &= df["neg_equity"] == 0
        df.loc[fill_mask, c] = medians[c]

    # 6칸 국가위험
    df["crc_unclassified"] = (df["oecd_crc"] == "-").astype(int)
    df["country_risk"] = pd.to_numeric(df["oecd_crc"].replace("-", 0)).astype(int)

    # 7칸 환율 변화
    df["fx_chg_30d"] = df["ccy"].map(lambda c: ref.loc[FX_AT_REF_CCY[c], "chg_30d"])
    fx_daily = fx_daily.sort_values("date").set_index("date")

    def rate_on_or_before(day, col):
        return fx_daily.loc[:day, col].iloc[-1]  # 휴일이면 직전 관측일

    d30, d60 = AS_OF - pd.Timedelta(days=30), AS_OF - pd.Timedelta(days=60)
    lag30 = {c: rate_on_or_before(d30, col) / rate_on_or_before(d60, col) - 1
             for c, col in FX_DAILY_COL.items()}
    df["fx_chg_30d_lag30"] = df["ccy"].map(lag30)

    # 결과 열 — 정의는 data/data_dictionary.xlsx(columns) 기준, 분모가 0이면 빈칸
    df["ccy_clean"] = df["ccy"]
    df["amt_num"] = df["ar_balance_num"]
    bal = df["amt_num"].where(df["amt_num"] != 0)
    df["pct_current"] = df["ar_current_num"] / bal
    df["pct_ar_31p"] = df[["ar_31_60_num", "ar_61_90_num", "ar_91p_num"]].sum(axis=1) / bal
    df["pct_91plus"] = df["ar_91p_num"] / bal
    df["avg_days_late"] = df["avg_days_late_12m"].astype(float)
    inv = df["invoices_12m"].astype(float).where(df["invoices_12m"] != 0)
    df["late_ratio"] = df["late_invoices_12m"].astype(float) / inv
    df["dispute_ratio"] = df["dispute_cnt_12m"].astype(float) / inv
    df["dpd_trend"] = df["avg_dpd_last3m"].astype(float) - df["avg_dpd_prev3m"].astype(float)

    # 결과 — buyer_id 첫 열, late_30d 끝 열
    out_cols = ["buyer_id", "payment_method", "ccy_clean", "amt_num", "ar_balance_usd",
                "pct_current", "pct_ar_31p", "pct_91plus", "max_dpd", "avg_days_late",
                "late_ratio", "dpd_trend", "dispute_ratio", *RATIO_COLS, "fin_missing",
                "neg_equity", "country_risk", "crc_unclassified", "unit_flag",
                "fx_chg_30d", "fx_chg_30d_lag30", "late_30d"]
    clean = df[out_cols]
    assert clean.shape == (150, 25) and clean["buyer_id"].is_unique
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUT_CSV, index=False, encoding="utf-8")

    write_report(raw, df, clean, medians, ratio_before, lag30, d30, d60, rate_on_or_before)
    print(f"저장: {OUT_CSV.relative_to(ROOT)} ({clean.shape[0]}행 × {clean.shape[1]}열)")
    print(f"저장: {OUT_REPORT.relative_to(ROOT)}")


def write_report(raw, df, clean, medians, ratio_before, lag30, d30, d60, rate_on_or_before):
    n = len(raw)
    text_before = {c: int(raw[c].map(is_text).sum()) for c in AR_COLS}
    text_after = {c: int(df[f"{c}_num"].map(is_text).sum()) for c in AR_COLS}
    raw_fin_na = {c: int(raw[c].isna().sum()) for c in FIN_FLAG_COLS + ["accounts_receivable", "operating_income"]}

    summary = md_table(["항목", "정제 전", "정제 후", "규칙"], [
        ["행 수", n, len(clean), "–"],
        ["통화 표기 종류", raw["currency"].nunique(), clean["ccy_clean"].nunique(), "1칸"],
        ["글자 섞인 금액 칸", sum(text_before.values()), sum(text_after.values()), "2칸"],
        ["비율 4열 빈칸 합계", int(ratio_before.isna().sum().sum()), int(clean[RATIO_COLS].isna().sum().sum()), "3칸 (남은 칸 = 자본잠식 D/E)"],
        ["fin_missing = 1", "–", int(clean["fin_missing"].sum()), "3칸"],
        ["단위 의심(USD 환산 잔액 > 한도 × 10)", int(df["unit_flag"].sum()),
         int((clean["ar_balance_usd"] > df["credit_limit_usd"] * 10).sum()), "4칸 (÷1,000 후)"],
        ["자기자본 0 이하", int((raw["equity"].astype(float) <= 0).sum()), int(clean["neg_equity"].sum()), "5칸 (플래그)"],
        ["oecd_crc 문자 '-'", int((raw["oecd_crc"] == "-").sum()), 0, "6칸 → crc_unclassified"],
        ["구간 합 ≠ 잔액", "–", int(df["amt_check"].sum()), "2칸 amt_check(보고서에만)"],
    ])

    derived = ["pct_current", "pct_ar_31p", "pct_91plus", "avg_days_late", "late_ratio", "dpd_trend", "dispute_ratio"]
    derived_why = {"pct_current": "amt_num = 0", "pct_ar_31p": "amt_num = 0", "pct_91plus": "amt_num = 0",
                   "avg_days_late": "invoices_12m = 0 (3칸: 채우지 않음)", "late_ratio": "invoices_12m = 0",
                   "dispute_ratio": "invoices_12m = 0", "dpd_trend": "최근 · 직전 3개월 중 한쪽이 없음"}
    derived_table = md_table(["열", "빈칸", "빈칸인 이유"],
                             [[c, int(clean[c].isna().sum()), derived_why[c]] for c in derived])

    ccy_rows = []
    for label, cnt in raw["currency"].value_counts().items():
        ccy_rows.append([f"`{label}`", cnt, MAP_CCY[label]])
    ccy_after = clean["ccy_clean"].value_counts()
    ccy_table = md_table(["원천 표기", "칸 수", "정제 후"], ccy_rows)
    ccy_after_table = md_table(["통화", "바이어 수"], [[k, v] for k, v in ccy_after.items()])

    text_rows = []
    for c in AR_COLS:
        for i in raw.index[raw[c].map(is_text)]:
            text_rows.append([raw.at[i, "buyer_id"], c, f"`{raw.at[i, c]!r}`", f"{df.at[i, f'{c}_num']:,.2f}"])
    text_table = md_table(["buyer_id", "열", "원천", "변환 값"], text_rows)

    na_table = md_table(["열", "정제 전 빈칸", "정제 후"], [
        *[[c, raw_fin_na[c], "원값은 출력하지 않음(비율 열로 대체)"] for c in raw_fin_na],
        *[[c, int(ratio_before[c].isna().sum()), int(clean[c].isna().sum())] for c in RATIO_COLS],
        *[[c, int(raw[c].isna().sum()), int(clean[c].isna().sum())] for c in ["avg_days_late_12m", "avg_dpd_last3m", "avg_dpd_prev3m"]],
    ])
    median_table = md_table(["비율 열", "대체 전 중위수", "채운 칸"], [
        [c, f"{medians[c]:.4f}", int(ratio_before[c].isna().sum() - clean[c].isna().sum())] for c in RATIO_COLS
    ])

    unit_rows = []
    for i in df.index[df["unit_flag"] == 1]:
        unit_rows.append([df.at[i, "buyer_id"], raw.at[i, "currency"], f"{to_number(raw.at[i, 'ar_balance']):,.0f}",
                          f"{df.at[i, 'ar_balance_num']:,.2f}", f"{df.at[i, 'ar_balance_usd']:,.2f}",
                          f"{df.at[i, 'credit_limit_usd']:,}"])
    unit_table = md_table(["buyer_id", "통화", "잔액(전)", "잔액(÷1,000 후)", "USD 환산", "한도(USD)"], unit_rows)

    check_rows = [[df.at[i, "buyer_id"], f"{df.at[i, 'ar_balance_num']:,.2f}",
                   f"{df.loc[i, [f'{c}_num' for c in BUCKETS]].sum():,.2f}"]
                  for i in df.index[df["amt_check"] == 1]]
    check_table = md_table(["buyer_id", "잔액", "다섯 구간 합"], check_rows)

    neg_table = md_table(["buyer_id", "equity", "debt_to_equity"], [
        [df.at[i, "buyer_id"], f"{float(df.at[i, 'equity']):,.0f}", "빈칸"] for i in df.index[df["neg_equity"] == 1]
    ])

    fx_rows = []
    for c, col in FX_DAILY_COL.items():
        fx_rows.append([c, f"{rate_on_or_before(d60, col):.2f}", f"{rate_on_or_before(d30, col):.2f}",
                        f"{lag30[c]:.4f}", f"{clean.loc[clean['ccy_clean'] == c, 'fx_chg_30d'].iloc[0]:.4f}"])
    fx_table = md_table(["통화", "60일 전(≤ 2026-07-02)", "30일 전(≤ 2026-08-01)", "fx_chg_30d_lag30", "fx_chg_30d"], fx_rows)

    sum_rows = []
    for c in ["USD", "EUR", "JPY", "CNY"]:
        m = df["ccy"] == c
        before = df.loc[m, "ar_balance_num"].where(df["unit_flag"] == 0, df["ar_balance_num"] * 1000).sum()
        after = df.loc[m, "ar_balance_num"].sum()
        adj = (df.loc[m & (df["unit_flag"] == 1), "ar_balance_num"] * 999).sum()
        sum_rows.append([c, f"{before:,.2f}", f"{after:,.2f}", f"{before - after:,.2f}", f"{adj:,.2f}",
                         "일치" if abs(before - after - adj) < 0.01 else "불일치"])
    sum_table = md_table(["통화", "잔액 합(숫자 변환 후, 보정 전)", "잔액 합(정제 후)", "차이", "단위 보정액", "대조"], sum_rows)

    report = f"""# 품질 보고서 — 2일차 buyers 정제 (전 · 후)

- 원본(읽기만): `data/checkpoints/d2_start.xlsx` 시트 `buyers` · `fx_at_ref`, `data/checkpoints/fx_krw_daily.csv`
- 규칙: `workbench/day2/rules/정제규칙.md` 1–7칸 · 기준일 2026-08-31
- 결과: `workbench/day2/outputs/d2_buyers_clean.csv` ({clean.shape[0]}행 × {clean.shape[1]}열)
- 만든 코드: `scripts/clean_buyers.py` — 아래 숫자는 모두 이 스크립트가 계산한 값입니다.

## 요약 — 정제 전 · 후

{summary}

## 1칸 통화 표기

{ccy_table}

정제 후:

{ccy_after_table}

## 2칸 글자 섞인 금액 칸

{text_table}

## 3칸 결측

{na_table}

{median_table}

### 결과 열의 빈칸 (분모가 0이거나 원천이 없음 — 채우지 않음)

{derived_table}

## 4칸 단위 의심

{unit_table}

## 2칸 구간 합 ≠ 잔액 (amt_check)

{check_table}

## 5칸 자본잠식

{neg_table}

## 7칸 환율 변화 (fx_krw_daily.csv · fx_at_ref)

{fx_table}

## 통화별 잔액 합계 대조

{sum_table}
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
