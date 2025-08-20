#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lineworks_cred_llm.py – クレド自動投稿（OllamaのローカルLLMを優先使用）
- LOCAL_LLM が設定されていれば Ollama 経由で生成
- 失敗時は事前定義クレドからランダムにフォールバック
- --dry-run ならログイン操作までは実施せず投稿もしない（生成のみ）
"""

from __future__ import annotations

import os
import sys
import re
import time
import random
import logging
import argparse
from datetime import date
from pathlib import Path

import jpholiday
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException


# ─────────── 定数 ─────────── #
LOGIN_URL = (
    "https://auth.worksmobile.com/login/login"
    "?accessUrl=https%3A%2F%2Ftalk.worksmobile.com%2F%23%2F"
)
TALK_URL = "https://talk.worksmobile.com/#/"
DEFAULT_WAIT_SEC = 240
ROOM_NAME = "●Team柳"

# ─────────── CLI ─────────── #
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="生成文を表示のみ（UI操作・投稿は行わない）")
args = parser.parse_args()

# ─────────── env & logger ─────────── #
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────── 認証情報 ─────────── #
LW_ID = os.getenv("LINEWORKS_ID", "")
LW_PASS = os.getenv("LINEWORKS_PASS", "")
if not LW_ID or not LW_PASS:
    logger.error("環境変数 LINEWORKS_ID / LINEWORKS_PASS を設定してください（.env 推奨）")
    sys.exit(1)

# ─────────── Chrome 設定 ─────────── #
CHROME_BINARY = os.getenv("CHROME_BINARY", "")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "")
HEADLESS = os.getenv("HEADLESS", "1")  # "0" で画面表示

# ─────────── Ollama（ローカルLLM）設定 ─────────── #
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
LOCAL_LLM = os.getenv("LOCAL_LLM", "").strip()  # 例: gpt-oss:20b / llama3.1:8b-instruct-q4_K_M

# ─────────── クレド定義（フォールバック用）─────────── #
CREDOS = {
    1: ("経営者目線", [
        "常に会社全体の利益と成長を考え、長期的視野で意思決定を行う。",
        "経営課題を自分事として捉え、オーナーシップを持って行動する。",
        "資源の有効活用を意識し、投資対効果を最大化する。",
        "事業戦略を理解し、日々の業務に経営視点を取り入れる。",
        "売上やコストの観点から業務プロセスを最適化する。",
    ]),
    2: ("好奇心100倍", [
        "未知の領域にも果敢に挑戦し、新たな知見を積極的に吸収する。",
        "疑問を持ったらすぐに調査し、深く掘り下げる姿勢を大切にする。",
        "常になぜを忘れず、成長の原動力とする。",
        "日常の小さな発見を軽視せず、好奇心を原動力に変える。",
        "新しい技術やアイデアに対して貪欲に情報収集する。",
    ]),
    3: ("世界最速", [
        "迅速かつ高品質な成果物を提供し、他社に差をつける。",
        "スピード感を持って課題解決に取り組み、常に先手を打つ。",
        "短期間で成果を出すことを意識し、無駄を排除する。",
        "リードタイムを最短化し、クライアントの期待を超える。",
        "決断を素早く行い、行動に移すスピードを追求する。",
    ]),
    4: ("言葉の達人", [
        "適切な言葉選びで、相手にわかりやすく情報を伝える。",
        "言葉の持つ力を理解し、説得力のあるコミュニケーションを行う。",
        "専門用語を咀嚼し、誰にでも理解できる表現に置き換える。",
        "声のトーンや話し方にも注意を払い、信頼感を醸成する。",
        "言葉で相手の心を動かし、共感を生む対話を心がける。",
    ]),
    5: ("問題解決のプロ", [
        "表面的な対症療法に終始せず、根本原因を徹底的に探ることで真の解決を図る。",
        "複雑な課題も要素分解し、論理的に解決策を導き出す。",
        "仮説を立てて迅速に検証し、最適解を見つけるアプローチを重視する。",
        "多角的な視点で問題を捉え、抜本的な改善を追求する。",
        "チームと連携して情報を集約し、効率的に課題を解決する。",
    ]),
    6: ("超一流の教育者", [
        "相手の理解度に合わせて、最適なタイミングで知識を提供する。",
        "学習意欲を引き出す工夫を凝らし、主体的な学びを支援する。",
        "フィードバックを欠かさず、成長を促す環境を整える。",
        "教育コンテンツを分かりやすく構造化し、効率的に伝える。",
        "相手の立場に立って指導し、信頼関係を築く。",
    ]),
    7: ("団結邁進", [
        "チームの目標を共有し、一丸となって前進する。",
        "メンバー同士が助け合い、高いパフォーマンスを発揮する。",
        "相互信頼を基盤に、困難な課題にも協力して立ち向かう。",
        "情報をオープンにし、全員が主体的に動ける環境を作る。",
        "チームワークを重視し、全員の力を結集して成果を生み出す。",
    ]),
    8: ("売上最大・経費最小", [
        "コスト意識を持って業務に取り組み、無駄を削減する。",
        "ROIを常に意識し、投資効果の最大化を図る。",
        "営業と経費管理のバランスを取り、効率的に利益を追求する。",
        "固定費と変動費を見極め、最適なコスト構造を実現する。",
        "売上拡大のための戦略とコスト削減策を同時に実行する。",
    ]),
    9: ("No.1 の精神", [
        "常にトップを目指し、現状に満足せず成長し続ける。",
        "競合に負けない品質とサービスを提供することを追求する。",
        "一歩先を行くアイデアと行動でリーダーシップを発揮する。",
        "自己ベンチマークを設定し、日々改善を繰り返す。",
        "チーム全体でNo.1を目指し、成功体験を共有する。",
    ]),
    10: ("率先邁進", [
        "自ら率先して行動し、周囲を巻き込んで成果を生む。",
        "先頭に立って課題にチャレンジし、道を切り開く。",
        "新しい取り組みに自信を持って挑戦し、模範を示す。",
        "指示を待たずに自主的に動き、チームを牽引する。",
        "行動力で周囲を鼓舞し、前進を促す。",
    ]),
    11: ("「相手」第一主義", [
        "相手のニーズを最優先に考え、最適な提案を行う。",
        "意図を深く理解し、期待以上のサービスを提供する。",
        "利害より信頼を重視し、相手本位のコミュニケーションを取る。",
        "相手の立場に立って言動ひとつひとつに思いやりを持って接する。",
        "課題を自分事として捉え、全力でサポートする。",
    ]),
    12: ("謙虚・誠実・熱心", [
        "成果に驕らず、常に謙虚な姿勢で学び続ける。",
        "誠実なコミュニケーションで信頼を築き、約束を守る。",
        "熱意を持って取り組み、困難にも前向きに挑む。",
        "周囲への感謝を忘れず、誠実に業務に臨む。",
        "謙虚さと情熱を両立させ、良い影響を与える。",
    ]),
    13: ("微差が大差", [
        "小さな改善を積み重ねることで大きな成果につなげる。",
        "細部へのこだわりが全体のクオリティを飛躍的に高める。",
        "日々のわずかな差が競合との差を生む原動力となる。",
        "小さな変化に気づき、速やかに実践することで優位を築く。",
        "微細な分析を怠らず、最適解を追求し続ける。",
    ]),
}

# ─────────── 後処理強化 ─────────── #
JPN_RE = re.compile(r"[^\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF。、：]")
MIN_LEN, MAX_LEN = 28, 70

def post_clean(text: str) -> str:
    text = text.strip(" 「」\n\t")
    text = JPN_RE.sub("", text)
    text = re.sub(r"^気づき：", "", text)
    if not text.endswith("。"):
        text += "。"
    return text

def is_bad(text: str) -> bool:
    n = len(text)
    return n < MIN_LEN or n > MAX_LEN


# ─────────── 生成ロジック（置き換え）─────────── #
def _clamp_length_jp(text: str, min_len: int = MIN_LEN, max_len: int = MAX_LEN) -> str:
    """日本語テキストを句点付きで規定長に丸める（長すぎ→切る／短すぎ→そのまま返す）"""
    s = post_clean(text)
    if len(s) > max_len:
        s = s[:max_len]
        if not s.endswith("。"):
            s = s.rstrip("、：") + "。"
    return s

def gen_credo_with_local_llm(idx: int, title: str) -> str:
    """Ollama ローカルLLMで生成（最大5回）
       - 1st: 通常生成
       - 短すぎ: 「同内容で50字前後に膨らませて再出力」を依頼
       - 最終手段: 24字以上なら許容、それ未満は失敗
    """
    if not LOCAL_LLM:
        raise RuntimeError("LOCAL_LLM not set")

    base_prompt = (
        f"{idx}. {title} の『気づき』を日本語のみで1文、40〜60文字で作成してください。\n"
        "・句点「。」で終える\n"
        "・英数字・記号は使わない\n"
        "・『気づき』『です・ます調』を使わない（常体）\n"
        "・主語を省き、具体的な行動や観点を1つだけ述べる\n"
        "・出力は本文のみ（前後に余計な語句や改行を付けない）"
    )

    payload = {
        "model": LOCAL_LLM,
        "options": {"temperature": 0.4, "top_p": 0.9, "num_ctx": 2048, "num_predict": 120},
        "stream": False,
    }

    def _ask(prompt: str) -> str:
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json={**payload, "prompt": prompt}, timeout=120)
        r.raise_for_status()
        return (r.json().get("response") or "").strip()

    last_err = None
    for attempt in range(5):
        try:
            if attempt == 0:
                raw = _ask(base_prompt)
            else:
                # 直前が短い場合の“増量リライト”プロンプト
                raw = _ask(
                    f"次の一文と同じ内容で、冗長にせず**50文字前後**に整えて出力してください。"
                    f"・英数字/記号は使わない ・句点で終える ・本文のみ\n「{cleaned}」"
                ) if 'cleaned' in locals() else _ask(base_prompt)

            cleaned = post_clean(raw)

            # まず長さが足りていればOK
            if MIN_LEN <= len(cleaned) <= MAX_LEN:
                return cleaned

            # 短い場合はもう一押し（次ループで増量リライト）
            if len(cleaned) < MIN_LEN:
                last_err = ValueError("too short")
                continue

            # 長すぎは安全に丸める
            cleaned = _clamp_length_jp(cleaned, MIN_LEN, MAX_LEN)
            if MIN_LEN <= len(cleaned) <= MAX_LEN:
                return cleaned
            last_err = ValueError(f"length {len(cleaned)} out of range")

        except Exception as e:
            last_err = e
            time.sleep(0.3)

    # 最終手段：24文字以上なら採用（どうしても短いモデル対策）
    if 'cleaned' in locals() and len(cleaned) >= 24:
        return _clamp_length_jp(cleaned, 24, MAX_LEN)

    raise last_err or RuntimeError("local llm generation failed")


# ─────────── Selenium ヘルパ ─────────── #
def build_driver() -> webdriver.Chrome:
    opts = Options()
    if HEADLESS != "0":
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    if CHROME_BINARY:
        opts.binary_location = CHROME_BINARY

    if CHROMEDRIVER_PATH and Path(CHROMEDRIVER_PATH).is_file():
        service = Service(executable_path=CHROMEDRIVER_PATH, start_timeout=240)
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        driver = webdriver.Chrome(options=opts)  # Selenium Manager に自動解決

    try:
        driver.set_page_load_timeout(180)
    except Exception:
        pass
    return driver


def _find_first(wait: WebDriverWait, selectors: list[tuple[By, str]]):
    last_exc = None
    for by, sel in selectors:
        try:
            return wait.until(EC.presence_of_element_located((by, sel)))
        except TimeoutException as e:
            last_exc = e
    raise last_exc or TimeoutException("element not found")


def switch_to_iframe_with_form(driver: webdriver.Chrome, wait: WebDriverWait):
    driver.switch_to.default_content()
    for frame in driver.find_elements(By.TAG_NAME, "iframe"):
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it(frame))
            if driver.find_elements(By.CSS_SELECTOR, "input[type='password']"):
                return
        except TimeoutException:
            continue
    driver.switch_to.default_content()


def wait_talk_app_ready(driver: webdriver.Chrome, wait: WebDriverWait):
    # DOM 完了
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    # 入力欄か検索欄のどちらかが出ればOK
    wait.until(EC.any_of(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.editor_input.message-input")),
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='検索']")),
    ))


def open_room(driver: webdriver.Chrome, wait: WebDriverWait, room_name: str) -> bool:
    logger.info("%sルームを探しています...", room_name)
    for attempt in range(1, 4):
        rooms = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "li[data-role='channel-item'], li[data-qa*='channel']")
        ))
        logger.info("ルーム検索試行 %d/3: %d個のルームが見つかりました", attempt, len(rooms))
        for room in rooms:
            text = room.text.strip()
            if room_name in text:
                logger.info("%sルームが見つかりました。クリックしています...", room_name)
                room.click()
                return True
        time.sleep(2)
    return False


# ─────────── main ─────────── #
def main() -> None:
    # 生成対象の抽選
    idx, (title, _) = random.choice(list(CREDOS.items()))

    # LLM優先で生成 → 失敗時フォールバック
    try:
        if LOCAL_LLM:
            body = gen_credo_with_local_llm(idx, title)
        else:
            raise RuntimeError("LOCAL_LLM not set")
    except Exception as e:
        logger.warning("ローカルLLM生成に失敗（%s）→ フォールバック使用", e)
        body = generate_credo_text(idx, title)

    message = (
        "【クレド報告】\n"
        "福原玄\n"
        f"＜クレドバリュー＞\n{idx}. {title}\n"
        f"＜気づき＞\n{body}"
    )
    logger.info("生成されたメッセージ:\n%s", message)

    # dry-run ならここで終わり
    logger.info("ブラウザを起動しています...")
    logger.info("=== using Python executable: %s ===", sys.executable)
    logger.info("=== ENV CHROMEDRIVER_PATH: %s", CHROMEDRIVER_PATH or "(auto)")
    logger.info("=== ENV CHROME_BINARY: %s", CHROME_BINARY or "(default)")
    logger.info("=== 実行開始: %s", date.today())
    if args.dry_run:
        logger.info("DRY RUN: 投稿は行いません。UI操作はここで終了します。")
        return

    # 任意スキップ（run_if_business_day.py 側でも制御するが、直実行対策）
    today = date.today().strftime("%Y-%m-%d")
    skip_env = {d.strip() for d in os.getenv("SKIP_DATES", "").split(",") if d.strip()}
    if today in skip_env or date.today().weekday() >= 5 or jpholiday.is_holiday(date.today()):
        logger.info("本日はクレド報告をスキップします。")
        return

    driver = None
    try:
        driver = build_driver()
        wait = WebDriverWait(driver, DEFAULT_WAIT_SEC)

        # 1) ログインID入力
        logger.info("LINE WORKSログインページにアクセスしています...")
        driver.get(LOGIN_URL)

        id_inp = _find_first(wait, [
            (By.CSS_SELECTOR, "input[name='loginId']"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ])
        logger.info("ユーザーIDを入力しています...")
        id_inp.clear()
        id_inp.send_keys(LW_ID)

        # 2) 次へ or ログイン
        logger.info("次へボタンをクリックしています...")
        btn = _find_first(wait, [
            (By.XPATH, "//button[contains(normalize-space(.),'次へ')]"),
            (By.XPATH, "//button[contains(normalize-space(.),'ログイン')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ])
        btn.click()

        # 3) パスワード
        logger.info("パスワード入力画面を探しています...")
        switch_to_iframe_with_form(driver, wait)
        logger.info("パスワードを入力しています...")
        pw = _find_first(wait, [(By.CSS_SELECTOR, "input[type='password']")])
        pw.clear()
        pw.send_keys(LW_PASS)
        logger.info("ログインボタンをクリックしています...")
        btn = _find_first(wait, [
            (By.XPATH, "//button[contains(normalize-space(.),'ログイン')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ])
        btn.click()
        driver.switch_to.default_content()

        # 4) Talk画面遷移
        logger.info("LINE WORKSトークページに移動しています...")
        try:
            talk_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href,'talk.worksmobile.com')]")
            ))
            talk_link.click()
            logger.info("トークページリンクをクリックしました")
        except TimeoutException:
            logger.warning("トークページリンクが見つからない場合の代替処理")
            driver.get(TALK_URL)
            logger.info("直接トークページにアクセスしました")

        wait_talk_app_ready(driver, wait)

        # 5) チャンネル選択
        if not open_room(driver, wait, ROOM_NAME):
            raise TimeoutException(f"チャンネル {ROOM_NAME} をUIから選択できませんでした")

        # 6) 投稿
        logger.info("メッセージ入力欄を探しています...")
        editor = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.editor_input.message-input")
        ))
        logger.info("メッセージ入力欄が見つかりました: div.editor_input.message-input")
        logger.info("メッセージを入力しています...")
        editor.click()
        editor.send_keys(message)

        logger.info("Ctrl+Enterでメッセージを送信しています...")
        ActionChains(driver).key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()

        try:
            WebDriverWait(driver, 10).until(EC.staleness_of(editor))
        except TimeoutException:
            pass

        logger.info("メッセージ送信完了🎉")

    except KeyboardInterrupt:
        logger.warning("ユーザーにより中断されました（Ctrl+C）")
    except Exception as e:
        logger.exception("❌ 予期せぬ例外: %s", e)
        # デバッグ用ダンプ
        try:
            png = "/tmp/cred_error.png"
            html = "/tmp/cred_error.html"
            driver.save_screenshot(png)
            Path(html).write_text(driver.page_source, encoding="utf-8")
            logger.error("デバッグ用に %s と %s を保存しました", png, html)
        except Exception:
            pass
        raise
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()

# ===== Added: safe fallback generator =====
def generate_credo_text(idx: int, title: str) -> str:
    """Local LLMが失敗したときの安全フォールバック。必ず十分な長さの本文を返す。"""
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d")
    # ここは自由に強化可（テンプレ or API フォールバック等）
    lines = [
        f"{now} クレド #{idx}：{title}",
        "【今日の学び】小さな改善でも続けることの価値に気づいた。",
        "【具体例】定例の手動作業を1つ自動化し、5分/日を削減。",
        "【チーム貢献】ノウハウを社内Wikiへ共有、質問1件に即レス。",
        "【明日の一歩】朝一でボトルネックの洗い出しと小改善を1件実行。"
    ]
    return "\n".join(lines)
