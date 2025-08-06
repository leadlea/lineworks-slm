#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lineworks_cred_llm.py  –  クレド自動投稿スクリプト
--dry-run で生成文を確認するだけ
"""

import os, random, re, logging, argparse
from datetime import date
from dotenv import load_dotenv
# from llama_cpp import Llama
# import openai  # OpenAI APIを使用する場合
import jpholiday

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

# ─────────── CLI ─────────── #
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="生成文を表示のみ")
args = parser.parse_args()

# ─────────── env & logger ─────────── #
load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─────────── LLM ─────────── #
MODEL_PATH = os.path.expanduser(os.getenv("ELYZA_MODEL_PATH", ""))
if not MODEL_PATH or not os.path.isfile(MODEL_PATH):
    logger.error("ELYZA_MODEL_PATH が見つかりません: %s", MODEL_PATH)
    exit(1)

# llm = Llama(model_path=MODEL_PATH, n_ctx=1024, n_threads=4, verbose=False)

# ─────────── 認証 ─────────── #
LW_ID   = os.getenv("LINEWORKS_ID")
LW_PASS = os.getenv("LINEWORKS_PASS")
if not LW_ID or not LW_PASS:
    logger.error(".env に LINEWORKS_ID / LINEWORKS_PASS を設定してください")
    exit(1)

CHROME_BINARY     = os.getenv("CHROME_BINARY")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")

# ─────────── クレド定義（省略なし） ─────────── #
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
        "常に『なぜ？』を忘れず、成長の原動力とする。",
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
        "一度話を聞いたら、その意図を深く理解し、期待以上のサービスを提供する。",
        "利害よりも信頼を重視し、相手本位のコミュニケーションを取る。",
        "相手の立場に立ち、言動ひとつひとつに思いやりを持って接する。",
        "相手が抱える課題を自分のことのように捉え、全力でサポートする。",
    ]),
    12: ("謙虚・誠実・熱心", [
        "成果に驕らず、常に謙虚な姿勢で学び続ける。",
        "誠実なコミュニケーションで信頼を築き、約束を守る。",
        "熱意を持って取り組み、困難にも前向きに挑む。",
        "周囲への感謝を忘れず、誠実に業務に臨む。",
        "謙虚さと情熱を両立させ、チームに良い影響を与える。",
    ]),
    13: ("微差が大差", [
        "小さな改善を積み重ねることで大きな成果につなげる。",
        "細部へのこだわりが全体のクオリティを飛躍的に高める。",
        "日々のわずかな差が競合との差を生む原動力となる。",
        "小さな変化に気づき、速やかに実践することで大きなアドバンテージを得る。",
        "微細な分析を怠らず、最適解を追求し続ける。",
    ]),
}

# ─────────── 生成ユーティリティ ─────────── #
ASCII_RE  = re.compile(r"[A-Za-z]+")
LONG_NUMS = re.compile(r"\d{3,}")              # 3 桁以上の数字列
DIGIT_RE  = re.compile(r"\d")

MIN_LEN, MAX_LEN = 28, 70

def post_clean(text: str) -> str:
    """英数字系ノイズを除去しフォーマット整える"""
    # 先頭・末尾のゴミ記号
    text = text.strip(" 「」\n\t")
    # 3 桁以上の数字列を丸ごと削除
    text = LONG_NUMS.sub("", text)
    # アルファベット削除
    text = ASCII_RE.sub("", text)
    # 全角以外の不要文字削除（日本語 + 。： のみ許可）
    text = re.sub(r"[^\wぁ-んァ-ン一-龯。、：]", "", text)
    # 「気づき：」を付与
    if not text.startswith("気づき："):
        text = "気づき：" + text
    # 終端
    if not text.endswith("。"):
        text += "。"
    return text

def is_bad(text: str) -> bool:
    n = len(text)
    # 数字が残っている／長さレンジ外／記号崩壊
    return n < MIN_LEN or n > MAX_LEN or DIGIT_RE.search(text) is not None or "気づき：" not in text

def generate_credo_text(idx: int, title: str) -> str:
    """ランダム選択 + バリエーション生成"""
    base_text = random.choice(CREDOS[idx][1])
    
    # 少しバリエーションを加える
    variations = [
        f"今日は{base_text}",
        f"改めて{base_text}",
        f"日々{base_text}",
        base_text
    ]
    
    selected = random.choice(variations)
    return f"気づき：{selected}"

# ─────────── Selenium util ─────────── #
def _find_first(driver, wait: WebDriverWait, selectors: list[tuple[By, str]]):
    last_exc = None
    for by, sel in selectors:
        try:
            return wait.until(EC.presence_of_element_located((by, sel)))
        except TimeoutException as e:
            last_exc = e
    raise last_exc or TimeoutException("element not found")

def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    if CHROME_BINARY:
        opts.binary_location = CHROME_BINARY
    if CHROMEDRIVER_PATH:
        service = Service(executable_path=CHROMEDRIVER_PATH)
        return webdriver.Chrome(service=service, options=opts)
    return webdriver.Chrome(options=opts)

# ─────────── main ─────────── #
def main() -> None:
    if not args.dry_run:
        d = date.today()
        if d.weekday() >= 5 or jpholiday.is_holiday(d):
            logger.info("本日はクレド報告をスキップします。")
            return

    idx, (title, _) = random.choice(list(CREDOS.items()))
    body = generate_credo_text(idx, title)
    msg = (
        f"【クレド報告】\n"
        f"福原玄\n"
        f"＜クレドバリュー＞\n{idx}. {title}\n"
        f"＜気づき＞\n{body}"
    )
    logger.info("生成されたメッセージ:\n%s", msg)

    if args.dry_run:
        print("=" * 40)
        print("DRY RUN: 生成されたメッセージ\n" + msg)
        print("=" * 40)
        return

    logger.info("ブラウザを起動しています...")
    driver = build_driver()
    wait = WebDriverWait(driver, 60)
    try:
        logger.info("LINE WORKSログインページにアクセスしています...")
        driver.get(
            "https://auth.worksmobile.com/login/login"
            "?accessUrl=https%3A%2F%2Ftalk.worksmobile.com%2F%23%2F"
        )
        logger.info("ユーザーIDを入力しています...")
        _find_first(driver, wait, [
            (By.CSS_SELECTOR, "input[name='loginId']"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]).send_keys(LW_ID)
        logger.info("次へボタンをクリックしています...")
        _find_first(driver, wait, [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(., 'ログイン')]"),
        ]).click()

        logger.info("パスワード入力画面を探しています...")
        for frame in driver.find_elements(By.TAG_NAME, "iframe"):
            driver.switch_to.frame(frame)
            if driver.find_elements(By.CSS_SELECTOR, "input[type='password']"):
                break
            driver.switch_to.default_content()

        logger.info("パスワードを入力しています...")
        _find_first(driver, wait, [(By.CSS_SELECTOR, "input[type='password']")]).send_keys(LW_PASS)
        logger.info("ログインボタンをクリックしています...")
        _find_first(driver, wait, [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button[contains(., 'ログイン')]"),
        ]).click()
        driver.switch_to.default_content()

        logger.info("LINE WORKSトークページに移動しています...")
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a[href*='talk.worksmobile.com']"))).click()
        logger.info("●Team柳ルームを探しています...")
        for room in wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "li[data-role='channel-item']"))):
            if "●Team柳" in room.text:
                logger.info("●Team柳ルームが見つかりました。クリックしています...")
                room.click(); break

        logger.info("メッセージ入力欄を探しています...")
        editor = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.editor_input.message-input")))
        logger.info("メッセージを入力しています...")
        editor.click(); editor.send_keys(msg)
        logger.info("Ctrl+Enterでメッセージを送信しています...")
        ActionChains(driver).key_down(Keys.CONTROL).send_keys(
            Keys.ENTER).key_up(Keys.CONTROL).perform()
        logger.info("メッセージ送信完了🎉")
    except Exception as e:
        logger.exception("送信中に例外が発生しました: %s", e)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
