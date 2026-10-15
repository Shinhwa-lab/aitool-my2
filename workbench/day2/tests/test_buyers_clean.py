"""정제 결과 d2_buyers_clean.csv가 정제규칙.md를 지키는지 보는 테스트 5개.

실행(저장소 맨 위 폴더)   uv run pytest -q
먼저 정제를 돌려 결과 파일을 만든다   uv run python scripts/clean_buyers.py
"""
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
CLEAN_CSV = ROOT / "workbench" / "day2" / "outputs" / "d2_buyers_clean.csv"


@pytest.fixture(scope="module")
def clean() -> pd.DataFrame:
    assert CLEAN_CSV.exists(), f"{CLEAN_CSV.relative_to(ROOT)} 없음 — 먼저 uv run python scripts/clean_buyers.py"
    return pd.read_csv(CLEAN_CSV)


def test_row_count(clean):
    assert len(clean) == 150


def test_buyer_id_unique(clean):
    dup = clean.loc[clean["buyer_id"].duplicated(keep=False), "buyer_id"].tolist()
    assert not dup, f"중복 buyer_id: {dup}"


def test_currency_four_kinds(clean):
    """1칸 — 표기 9가지가 USD · EUR · JPY · CNY 4종으로 통일됐다."""
    assert set(clean["ccy_clean"]) == {"USD", "EUR", "JPY", "CNY"}


@pytest.mark.parametrize("col", ["amt_num", "ar_balance_usd"])
def test_amount_non_negative(clean, col):
    """2칸 — 숫자로 바뀌지 않은 칸(빈칸)도, 음수도 없다."""
    assert clean[col].notna().all(), f"{col} 빈칸: {clean.loc[clean[col].isna(), 'buyer_id'].tolist()}"
    assert (clean[col] >= 0).all(), f"{col} 음수: {clean.loc[clean[col] < 0, 'buyer_id'].tolist()}"


def test_b072_unit_flag(clean):
    """4칸 — B072(8,320,000 euro)만 단위 의심이고, ÷1,000 해서 구간 합 8,320과 같다."""
    flagged = clean.loc[clean["unit_flag"] == 1, "buyer_id"].tolist()
    assert flagged == ["B072"]
    b072 = clean.set_index("buyer_id").loc["B072"]
    assert b072["amt_num"] == pytest.approx(8320)
    assert b072["ar_balance_usd"] <= 10_000 * 10
