"""2일차 스케일 비교 — revenue를 로그 변환한 뒤 Min-Max · 표준화로 바꿔 바이어 3곳을 견준다.

실행: `uv run python scripts/scaling_revenue.py`
입력(읽기만): data/checkpoints/d2_start.xlsx (buyers)
출력: workbench/day2/outputs/scaling.md — 비교용 표만 만들고 특성 파일(d2_buyers_clean.csv)에는 넣지 않는다.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC_XLSX = ROOT / "data/checkpoints/d2_start.xlsx"
OUT_MD = ROOT / "workbench/day2/outputs/scaling.md"


def main():
    raw = pd.read_excel(SRC_XLSX, sheet_name="buyers")
    rev = raw.set_index("buyer_id")["revenue"].dropna().astype(float)  # 빈칸 18곳은 빼고 비교

    log_rev = np.log(rev)
    mm_raw = (rev - rev.min()) / (rev.max() - rev.min())
    mm_log = (log_rev - log_rev.min()) / (log_rev.max() - log_rev.min())
    z_log = (log_rev - log_rev.mean()) / log_rev.std(ddof=0)

    picks = {
        "최소": log_rev.idxmin(),
        "중앙값 근처": (log_rev - log_rev.median()).abs().idxmin(),
        "최대": log_rev.idxmax(),
    }
    rows = []
    for label, b in picks.items():
        rows.append(f"| {label} | {b} | {rev[b]:,.0f} | {mm_raw[b]:.4f} | {log_rev[b]:.4f} "
                    f"| {mm_log[b]:.4f} | {z_log[b]:+.4f} |")

    report = f"""# 스케일 비교 — revenue (로그 → Min-Max · 표준화)

- 원본(읽기만): `data/checkpoints/d2_start.xlsx` 시트 `buyers` 열 `revenue`(USD)
- 대상: revenue가 있는 {len(rev)}곳 (빈칸 {int(raw['revenue'].isna().sum())}곳 제외 — 비교만 하므로 채우지 않음)
- 로그: 자연로그 `ln(revenue)` · Min-Max: `(x − min) ÷ (max − min)` · 표준화: `(x − 평균) ÷ 표준편차`(모표준편차, ddof=0)
- 만든 코드: `scripts/scaling_revenue.py` — 이 표는 비교용이며 특성 파일 `d2_buyers_clean.csv`에는 넣지 않는다.

| 위치 | buyer_id | revenue (USD) | Min-Max (원값) | ln(revenue) | Min-Max (로그) | 표준화 (로그) |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

로그 변환 기준값: 최소 {log_rev.min():.4f} · 중앙값 {log_rev.median():.4f} · 최대 {log_rev.max():.4f} · 평균 {log_rev.mean():.4f} · 표준편차 {log_rev.std(ddof=0):.4f}
"""
    OUT_MD.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
