"""2일차 뉴스 채점 검사 — `workbench/day2/prompts/news_score_v1.md` 출력 형식을 news_scored.jsonl에 대어 본다.

실행: `uv run python scripts/validate_scores.py`
입력(읽기만): workbench/day2/outputs/news_scored.jsonl · data/checkpoints/d2_news.csv
검사: ① 100줄 ② news_sent_0_10이 0–10 정수 ③ label이 점수 대역과 맞음
      ④ evidence가 원문 headline 또는 body_short 안에 글자 그대로 있음
출력: 위반 행만 화면에 적고, 위반이 있으면 종료 코드 1.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_NEWS = ROOT / "data/checkpoints/d2_news.csv"
SCORED = ROOT / "workbench/day2/outputs/news_scored.jsonl"

EXPECTED_LINES = 100


def band_label(score):
    """규칙 5 — 0–2 severe · 3–4 high · 5 watch · 6–10 low."""
    if score <= 2:
        return "severe"
    if score <= 4:
        return "high"
    if score == 5:
        return "watch"
    return "low"


def check_line(rec, src):
    """한 줄의 위반 사유 목록. 비어 있으면 통과."""
    problems = []
    score = rec.get("news_sent_0_10")
    # bool은 int의 하위형이라 따로 막는다(true가 1점으로 통과하지 않게)
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 10:
        problems.append(f"점수가 0–10 정수가 아님: {score!r}")
    elif rec.get("label") != band_label(score):
        problems.append(f"라벨 불일치: {score}점 → {band_label(score)}인데 {rec.get('label')!r}")

    if src is None:
        problems.append(f"원문에 없는 news_id: {rec.get('news_id')!r}")
    else:
        ev = rec.get("evidence")
        if not isinstance(ev, str) or not ev or (ev not in src["headline"] and ev not in src["body_short"]):
            problems.append(f"evidence가 원문 headline·body_short에 그대로 없음: {ev!r}")
    return problems


def main():
    # Windows 콘솔(cp949)에 없는 글자(— · 베트남어 등)로 print가 죽지 않게 한다
    sys.stdout.reconfigure(errors="backslashreplace")
    with open(SRC_NEWS, encoding="utf-8-sig", newline="") as f:
        src_by_id = {r["news_id"]: r for r in csv.DictReader(f)}
    lines = SCORED.read_text(encoding="utf-8").splitlines()

    violations = []
    if len(lines) != EXPECTED_LINES:
        violations.append(f"줄 수: {len(lines)}줄 (기대 {EXPECTED_LINES}줄)")

    for n, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            violations.append(f"{n}행: JSON 아님 ({e})")
            continue
        for p in check_line(rec, src_by_id.get(rec.get("news_id"))):
            violations.append(f"{n}행 {rec.get('news_id')}: {p}")

    if violations:
        print(f"위반 {len(violations)}건")
        for v in violations:
            print(" -", v)
        sys.exit(1)
    print(f"통과 — {len(lines)}줄, 점수 · 라벨 · evidence 모두 규칙대로")


if __name__ == "__main__":
    main()
