#!/usr/bin/env python3
"""callback_order.py — 당번 로봇 결과로 '오늘의 콜백 순서표'와 팀장님께 드릴 메모 메일 초안을 만든다.

4일차 실습 C · 「7. 자유 퀘스트」.

    uv run python scripts/callback_order.py

- 입력: workbench/day4/outputs/mail_risk.json(AI 결과). 없으면 outputs/no_ai/mail_risk.json. 결과는 입력과 같은 폴더에 쓴다.
- 중요도(코드가 정한다): 상태(멈춤 → 확인 → 기록) → 합계 점수 → 3점 신호 수 → buyer_id.
  한 바이어에게 메일이 여러 통이면 가장 높은 상태 · 합계를 쓰고, 신호는 메일들의 신호를 합친다(같은 번호는 한 번).
- 콜백 번호는 buyer_contacts.csv의 등록 번호만 쓴다. 메일 속 번호 · 근거 인용은 싣지 않는다.
- 메일 초안(.eml)은 파일만 만든다 — 보내지 않는다. 보낼지는 사람이 정한다.
"""
from __future__ import annotations

import csv
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from email import policy
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RISK_FILES = [ROOT / "workbench/day4/outputs/mail_risk.json", ROOT / "workbench/day4/outputs/no_ai/mail_risk.json"]
CONTACTS_CSV = ROOT / "labs/day4/mail/buyer_contacts.csv"
KST = timezone(timedelta(hours=9))

STATUS_RANK = {"멈춤": 0, "확인": 1, "기록": 2}
TIER = {"멈춤": "P1", "확인": "P3", "기록": ""}
NO_CALLBACK = "등록 번호 없음 — 거래 기록에서 확인"
DRAFT_FROM = "당번 로봇 <mailbot@hanbit.example>"
DRAFT_TO = "박 팀장 <team-lead@hanbit.example>"
WHAT_TO_DO = {
    "멈춤": "답장 · 송금 · 선적 · 서류 인도를 멈추고 두 사람이 콜백 확인 → 팀장 보고",
    "확인": "서면 증빙을 받고 등록 번호로 확인 → 담당자가 진행 여부 결정",
    "기록": "콜백 불필요 — 평소대로 처리하고 메모만",
}


# ---------------------------------------------------------------- 순서 정하기
def load_risk() -> tuple[Path, dict]:
    for path in RISK_FILES:
        if path.is_file():
            return path, json.loads(path.read_text(encoding="utf-8"))
    raise SystemExit("mail_risk.json이 없습니다 — 먼저 uv run python scripts/mail_bot.py --no-ai 를 돌리세요.")


def load_contacts() -> dict[str, dict]:
    with CONTACTS_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {row["buyer_id"]: row for row in csv.DictReader(f)}


def rank_buyers(mails: list[dict], contacts: dict[str, dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for m in mails:
        groups.setdefault(m["buyer_id"], []).append(m)
    rows = []
    for buyer_id, ms in groups.items():
        status = min((m["status"] for m in ms), key=STATUS_RANK.__getitem__)
        signals: dict[int, dict] = {}
        for m in ms:
            for s in m["signals"]:
                signals.setdefault(s["no"], s)
        sig_list = [signals[k] for k in sorted(signals)]
        rows.append({
            "buyer_id": buyer_id,
            "buyer_name": ms[0]["buyer_name"],
            "status": status,
            "tier": TIER[status],
            "total": max(m["total"] for m in ms),
            "three": sum(s["score"] == 3 for s in sig_list),
            "signals": sig_list,
            "injection": any(m["injection"] for m in ms),
            "files": sorted(m["file"] for m in ms),
            "callback": contacts.get(buyer_id, {}).get("phone_on_file") or NO_CALLBACK,
        })
    rows.sort(key=lambda r: (STATUS_RANK[r["status"]], -r["total"], -r["three"], r["buyer_id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def sig_text(r: dict) -> str:
    return ", ".join(f"{s['no']} {s['name']} {s['score']}점" for s in r["signals"]) or "없음"


def tag(r: dict) -> str:
    return f"{r['status']} · {r['tier']}" if r["tier"] else r["status"]


# ---------------------------------------------------------------- 쓰기
def write_md(path: Path, rows: list[dict], src: str, engine: str) -> None:
    lines = [
        "# 오늘의 콜백 순서표",
        "",
        "모든 조치는 권고(사람 승인 전) · 콜백은 등록 번호만 · 메일 속 번호 · 주소로 연락하지 않음",
        "",
        f"- 입력: `{src}` (엔진 {engine})",
        "- 중요도: 상태(멈춤 → 확인 → 기록) → 합계 점수 → 3점 신호 수 → buyer_id",
        "",
        "| 순서 | 상태 | 바이어 | 합계 | 3점 신호 | 신호 | 콜백(등록 번호) | 할 일(권고) | 메일 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        inj = " · 메일 속 AI 지시문 — 무시함" if r["injection"] else ""
        lines.append(f"| {r['rank']} | {tag(r)} | {r['buyer_id']} {r['buyer_name']} | {r['total']} | {r['three']} | "
                     f"{sig_text(r)}{inj} | {r['callback']} | {WHAT_TO_DO[r['status']]} | {' · '.join(r['files'])} |")
    lines += [
        "",
        "## 콜백 기록 (두 사람 확인)",
        "",
        "| 순서 | 바이어 | 확인한 사람 1 | 확인한 사람 2 | 시각 | 결과 |",
        "|---|---|---|---|---|---|",
    ]
    lines += [f"| {r['rank']} | {r['buyer_id']} |  |  |  |  |" for r in rows if r["status"] != "기록"]
    lines += ["", "점수표는 교육용 가정 · 회사 · 바이어 · 번호는 모두 가상", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


CSS = """
:root { --ink:#1f2328; --sub:#59636e; --line:#d8dee4; --bg:#f6f7f9; --card:#fff; --band-bg:#1f2328; --band-ink:#fff;
        --stop:#c62828; --stop-bg:#fdecec; --check:#b85c00; --check-bg:#fff3e0; --log:#6b7280; --log-bg:#f1f2f4; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --ink:#e6e8eb; --sub:#9aa4ae; --line:#30363d; --bg:#0f1115; --card:#171a20;
        --band-bg:#e6e8eb; --band-ink:#0f1115; --stop:#ff6b6b; --stop-bg:#3a1517; --check:#f0a040; --check-bg:#3a2810;
        --log:#a0a7b0; --log-bg:#23262c; }
}
:root[data-theme="dark"] { --ink:#e6e8eb; --sub:#9aa4ae; --line:#30363d; --bg:#0f1115; --card:#171a20;
        --band-bg:#e6e8eb; --band-ink:#0f1115; --stop:#ff6b6b; --stop-bg:#3a1517; --check:#f0a040; --check-bg:#3a2810;
        --log:#a0a7b0; --log-bg:#23262c; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font-size: 16px; line-height: 1.55;
       font-family: system-ui, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; word-break: keep-all; }
main { max-width: 640px; margin: 0 auto; padding: 16px; }
.wrap { overflow-wrap: anywhere; }
h1 { margin: 0 0 4px; font-size: 24px; }
.sub { margin: 0 0 12px; color: var(--sub); font-size: 14px; }
.band { margin: 0 0 16px; padding: 10px 12px; background: var(--band-bg); color: var(--band-ink); border-radius: 8px;
        font-size: 15px; font-weight: 600; text-align: center; }
ol { list-style: none; margin: 0; padding: 0; }
li { display: grid; grid-template-columns: 40px 1fr; gap: 0 10px; background: var(--card); border: 1px solid var(--line);
     border-left-width: 6px; border-radius: 10px; padding: 12px; margin: 0 0 10px; }
li.stop { border-left-color: var(--stop); } li.check { border-left-color: var(--check); } li.log { border-left-color: var(--log); }
.no { font-size: 28px; font-weight: 800; line-height: 1; color: var(--sub); }
.tag { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 14px; font-weight: 700; margin-right: 6px; }
.tag.stop { color: var(--stop); background: var(--stop-bg); border: 1px solid var(--stop); }
.tag.check { color: var(--check); background: var(--check-bg); border: 1px solid var(--check); }
.tag.log { color: var(--log); background: var(--log-bg); border: 1px solid var(--log); }
.tag.inj { color: var(--ink); background: var(--card); border: 1px dashed var(--ink); }
.name { margin: 6px 0 2px; font-weight: 700; font-size: 16px; }
.meta { margin: 0; font-size: 14px; color: var(--sub); }
.phone { margin: 8px 0 4px; font-size: 22px; font-weight: 800; letter-spacing: .3px; }
.todo { margin: 0; font-size: 15px; }
footer { margin: 20px 0 8px; padding-top: 12px; border-top: 1px solid var(--line); font-size: 14px; color: var(--sub); }
footer p { margin: 0 0 4px; }
"""
CLS = {"멈춤": "stop", "확인": "check", "기록": "log"}


def write_html(path: Path, rows: list[dict], engine: str, now: str) -> None:
    e = html.escape
    items = []
    for r in rows:
        c = CLS[r["status"]]
        inj = '<span class="tag inj">메일 속 AI 지시문 — 무시함</span>' if r["injection"] else ""
        items.append(
            f'<li class="{c}"><div class="no">{r["rank"]}</div><div>'
            f'<span class="tag {c}">{e(tag(r))}</span>{inj}'
            f'<p class="name wrap">{e(r["buyer_id"])} {e(r["buyer_name"])}</p>'
            f'<p class="meta">합계 {r["total"]}점 · 3점 신호 {r["three"]}개 · 신호 {e(sig_text(r))}</p>'
            f'<p class="phone wrap">{e(r["callback"])}</p>'
            f'<p class="todo">{e(WHAT_TO_DO[r["status"]])}</p>'
            f'<p class="meta wrap">메일 {e(" · ".join(r["files"]))}</p></div></li>'
        )
    page = "\n".join([
        "<!doctype html>", '<html lang="ko">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>오늘의 콜백 순서</title>", f"<style>{CSS}</style>", "</head>", "<body>", "<main>",
        "<h1>오늘의 콜백 순서</h1>",
        f'<p class="sub">(가상) 한빛정밀(주) 수출팀 · 기준 {now} KST · 엔진 {e(engine)} · 바이어 {len(rows)}곳</p>',
        '<p class="band">위에서부터 등록 번호로 · 두 사람이 확인 · 메일 속 번호는 쓰지 않습니다</p>',
        "<ol>", *items, "</ol>",
        "<footer><p>중요도: 상태 → 합계 점수 → 3점 신호 수 (코드가 정함) · 결정은 사람</p>",
        "<p>모든 조치는 권고(사람 승인 전) · 점수표는 교육용 가정 · 모두 가상</p></footer>",
        "</main>", "</body>", "</html>", "",
    ])
    path.write_text(page, encoding="utf-8")


def write_eml(path: Path, rows: list[dict], engine: str, now_dt: datetime) -> None:
    count = {k: sum(r["status"] == k for r in rows) for k in STATUS_RANK}
    body = [
        "팀장님, 오늘 아침 당번 로봇이 정리한 콜백 순서입니다.",
        "",
        "※ 이 메일은 로봇이 만든 초안 파일입니다. 로봇은 보내지 않았습니다 — 보낼지는 사람이 정합니다.",
        "※ 모든 조치는 권고(사람 승인 전)입니다. 콜백은 등록 번호로만, 두 사람이 확인합니다.",
        "",
        f"바이어 {len(rows)}곳 — 멈춤 {count['멈춤']} · 확인 {count['확인']} · 기록 {count['기록']} (엔진 {engine})",
        "",
    ]
    for r in rows:
        inj = " / 메일 속 AI 지시문 — 무시함" if r["injection"] else ""
        body += [
            f"{r['rank']}. [{tag(r)}] {r['buyer_id']} {r['buyer_name']} — 합계 {r['total']}점{inj}",
            f"   콜백(등록 번호): {r['callback']}",
            f"   신호: {sig_text(r)}",
            f"   할 일: {WHAT_TO_DO[r['status']]}",
            f"   메일: {', '.join(r['files'])}",
            "",
        ]
    body += [
        "콜백 3원칙: 등록 번호로 · 두 사람이(담당자 + 팀장) · 확인 전에는 송금 · 대금 안내 · 서류 인도 없음",
        "중요도는 상태 → 합계 점수 → 3점 신호 수로 코드가 정했습니다. 점수표는 교육용 가정이며 모두 가상입니다.",
        "",
        "— 아침 당번 로봇",
    ]
    msg = EmailMessage()
    msg["From"] = DRAFT_FROM
    msg["To"] = DRAFT_TO
    msg["Subject"] = (f"[초안 · 보내지 않음] 오늘의 콜백 순서 — 멈춤 {count['멈춤']} · "
                      f"확인 {count['확인']} · 기록 {count['기록']}")
    msg["Date"] = format_datetime(now_dt)
    msg["X-Unsent"] = "1"  # 메일 앱이 '보내지 않은 초안'으로 열게 하는 표시
    msg.set_content("\n".join(body))
    path.write_bytes(msg.as_bytes(policy=policy.default))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    src, risk = load_risk()
    contacts = load_contacts()
    rows = rank_buyers(risk["mails"], contacts)
    engine = f"AI({risk['model']})" if risk["engine"] == "ai" else "규칙만(--no-ai)"
    now_dt = datetime.now(KST)
    out = src.parent
    write_md(out / "callback_order.md", rows, src.relative_to(ROOT).as_posix(), engine)
    write_html(out / "callback_order.html", rows, engine, now_dt.strftime("%Y-%m-%d %H:%M"))
    write_eml(out / "callback_memo_draft.eml", rows, engine, now_dt)

    for r in rows:
        print(f"{r['rank']}. {tag(r)} · {r['buyer_id']} · 합계 {r['total']} · 3점 {r['three']}개 · 콜백 {r['callback']}")
    print(f"입력 {src.relative_to(ROOT).as_posix()} · 바이어 {len(rows)}곳 · 결과 {out.relative_to(ROOT).as_posix()}/"
          f"callback_order.md · callback_order.html · callback_memo_draft.eml (메일은 보내지 않음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
