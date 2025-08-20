#!/usr/bin/env python3
"""
平日かつ非祝日かつ「指定除外日」でない場合のみ、指定スクリプトを実行するラッパー

USAGE:
  1) 引数なし: デフォルトで src/lineworks_cred_llm.py を実行
       ./run_if_business_day.py
  2) 任意のスクリプトを明示:
       ./run_if_business_day.py path/to/script.py [args...]

除外日の指定方法:
- .env に SKIP_DATES="2025-08-15, 12-31" のようにカンマ/空白区切りで列挙
  * YYYY-MM-DD 形式はその年のピンポイント除外
  * MM-DD      形式は毎年同じ日を除外（例: 12-31）
- または、スクリプトと同じディレクトリの skip_dates.txt に1行1つで列挙（#でコメント可）
- 環境変数 SKIP_DATES_FILE で別ファイルパスも指定可能
"""

import datetime as dt
import os
import re
import sys
import subprocess
from pathlib import Path

import jpholiday
from dotenv import load_dotenv


def is_business(day: dt.date) -> bool:
    """月〜金かつ祝日でないかを判定する。"""
    return day.weekday() < 5 and not jpholiday.is_holiday(day)


def parse_tokens(s: str):
    """SKIP_DATES などの文字列をパースして、日付集合を返す。"""
    full_dates: set[dt.date] = set()        # YYYY-MM-DD 固定日
    recur_md: set[tuple[int, int]] = set()  # (MM,DD) 毎年
    if not s:
        return full_dates, recur_md
    for tok in re.split(r"[,\s]+", s.strip()):
        if not tok:
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tok):
            y, m, d = map(int, tok.split("-"))
            full_dates.add(dt.date(y, m, d))
        elif re.fullmatch(r"\d{2}-\d{2}", tok):
            m, d = map(int, tok.split("-"))
            recur_md.add((m, d))
        else:
            # 不正フォーマットは黙って無視
            pass
    return full_dates, recur_md


def load_skip_dates(base: Path):
    """環境変数とファイルから除外日を読み込む。"""
    full_dates: set[dt.date] = set()
    recur_md: set[tuple[int, int]] = set()

    # 1) 環境変数 SKIP_DATES
    f1, r1 = parse_tokens(os.environ.get("SKIP_DATES", ""))
    full_dates |= f1
    recur_md |= r1

    # 2) ファイル（デフォルトは ./skip_dates.txt）
    file_path = os.environ.get("SKIP_DATES_FILE") or str(base / "skip_dates.txt")
    p = Path(file_path)
    if p.exists():
        for raw in p.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            f2, r2 = parse_tokens(line)
            full_dates |= f2
            recur_md   |= r2

    return full_dates, recur_md


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    today = dt.date.today()

    # Homebrew 等のPATHを先頭に
    for prefix in ("/usr/local/bin", "/opt/homebrew/bin"):
        os.environ["PATH"] = prefix + os.pathsep + os.environ.get("PATH", "")

    # .env を読み込んで環境に反映（既存値より .env を優先）
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)

    # 除外日読み込み
    full_dates, recur_md = load_skip_dates(script_dir)

    # 指定除外日チェック
    if (today in full_dates) or ((today.month, today.day) in recur_md):
        print(f"[skip] {today} は指定除外日")
        return 0

    # 平日・祝日チェック
    if not is_business(today):
        print(f"[skip] {today} は休日/祝日")
        return 0

    # 実行ターゲット決定（引数なければ既定スクリプト）
    if len(sys.argv) >= 2:
        target_rel = sys.argv[1]
        extra_args = sys.argv[2:]
    else:
        target_rel = "src/lineworks_cred_llm.py"
        extra_args = []

    target = (script_dir / target_rel).resolve()

    # 使うPython：プロジェクトの .venv 優先、なければ現在のPython
    venv_py = script_dir / ".venv" / "bin" / "python"
    python_bin = venv_py if venv_py.exists() else Path(sys.executable)

    if not target.exists():
        print(f"[err] ターゲットが見つかりません: {target}", file=sys.stderr)
        return 2

    print(f"[run] {today} 平日判定 OK → {target.name}")
    # 実行（作業ディレクトリはプロジェクトルート）
    proc = subprocess.run(
        [str(python_bin), str(target), *extra_args],
        cwd=str(script_dir)
    )
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
