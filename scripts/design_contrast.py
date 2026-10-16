"""3일차 실습 D — design.md 토큰의 글자 · 바탕 대비(WCAG 2.x)를 계산해 design.md 「5. 대비 표」에 쓴다.

실행: `uv run python scripts/design_contrast.py`
입력 · 출력: workbench/day3/outputs/design.md (토큰 표의 `--이름` | `#RRGGBB` 줄을 읽고, contrast 표시 사이만 다시 쓴다)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "workbench/day3/outputs/design.md"
MIN_RATIO = 4.5

# (무엇 · 글자 토큰 · 바탕 토큰)
PAIRS = [
    ("본문 글자", "--text", "--bg"),
    ("본문 글자", "--text", "--surface"),
    ("보조 글자", "--text-2", "--bg"),
    ("보조 글자", "--text-2", "--surface"),
    ("강조 글자(슬라이더 값 · 링크)", "--accent", "--surface"),
    ("안내 띠 글자", "--surface", "--accent"),
    ("등급 라벨 S", "--surface", "--grade-s"),
    ("등급 라벨 A", "--surface", "--grade-a"),
    ("등급 라벨 B", "--surface", "--grade-b"),
    ("등급 라벨 C", "--surface", "--grade-c"),
]


def luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg, bg):
    hi, lo = sorted([luminance(fg), luminance(bg)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def main():
    text = DESIGN.read_text(encoding="utf-8")
    tokens = dict(re.findall(r"^\| `(--[\w-]+)` \| `(#[0-9A-Fa-f]{6})` \|", text, flags=re.M))

    rows = ["| 무엇 | 글자 | 바탕 | 대비 | 4.5 : 1 이상 |", "|---|---|---|---:|---|"]
    results = []
    for what, fg, bg in PAIRS:
        r = contrast(tokens[fg], tokens[bg])
        results.append((what, fg, bg, r))
        ok = "통과" if r >= MIN_RATIO else "미달 — 색을 고쳐 다시"
        rows.append(f"| {what} | `{fg}` {tokens[fg]} | `{bg}` {tokens[bg]} | {r:.2f} : 1 | {ok} |")
    low = min(results, key=lambda x: x[3])
    rows.append("")
    rows.append(f"가장 낮은 값: {low[0]} {low[3]:.2f} : 1")

    block = "<!-- contrast:start -->\n" + "\n".join(rows) + "\n<!-- contrast:end -->"
    new = re.sub(r"<!-- contrast:start -->.*?<!-- contrast:end -->", lambda m: block, text, flags=re.S)
    DESIGN.write_text(new, encoding="utf-8")

    for what, fg, bg, r in results:
        print(f"{what:<28} {fg:<10} on {bg:<10} {r:5.2f} {'OK' if r >= MIN_RATIO else 'FAIL'}")
    print(f"가장 낮은 값: {low[0]} {low[3]:.2f}")


if __name__ == "__main__":
    main()
