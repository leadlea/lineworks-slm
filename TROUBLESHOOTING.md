# トラブルシューティングガイド

## よくある問題と解決方法

### 1. ChromeDriverの問題

#### 症状: "chromedriver executable needs to be in PATH"
```bash
# ChromeDriverがインストールされているか確認
which chromedriver

# インストールされていない場合
brew install chromedriver

# パスを.envファイルに設定
echo "CHROMEDRIVER_PATH=$(which chromedriver)" >> .env
```

#### 症状: ChromeDriverとChromeのバージョン不一致
```bash
# Chromeのバージョン確認
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version

# ChromeDriverのバージョン確認
chromedriver --version

# バージョンが合わない場合
brew upgrade chromedriver
```

### 2. Python依存関係の問題

#### 症状: "ModuleNotFoundError: No module named 'selenium'"
```bash
# 依存関係を再インストール
pip install -r requirements.txt

# 特定のパッケージが問題の場合
pip install --upgrade selenium
```

#### 症状: "llama_cpp import error"
現在のバージョンではLLMライブラリは使用していません。エラーが出る場合は以下を確認：
```python
# src/lineworks_cred_llm.py の11行目がコメントアウトされているか確認
# from llama_cpp import Llama
```

### 3. LINE WORKS投稿の問題

#### 症状: ログイン失敗
1. `.env`ファイルの認証情報を確認
2. LINE WORKSのパスワードが変更されていないか確認
3. 2段階認証が有効になっていないか確認

#### 症状: "●Team柳ルームが見つからない"
1. ルーム名が正確か確認
2. ルームへのアクセス権限があるか確認
3. ルーム名が変更されていないか確認

#### 症状: メッセージ送信失敗
1. ネットワーク接続を確認
2. LINE WORKSのサービス状況を確認
3. ログファイルで詳細なエラーを確認

### 4. 自動実行の問題

#### 症状: launchdサービスが動作しない
```bash
# サービス状態確認
launchctl list | grep lineworks

# サービスが登録されていない場合
launchctl load ~/Library/LaunchAgents/com.gen.lineworks.cred.llm.plist

# 権限問題の場合
chmod 644 ~/Library/LaunchAgents/com.gen.lineworks.cred.llm.plist
```

#### 症状: スケジュール通りに実行されない
1. システム時刻が正確か確認
2. macOSのスリープ設定を確認
3. ログファイルでエラーを確認

### 5. ログの確認方法

#### 出力ログの確認
```bash
tail -f cron_logs/lineworks_cred_llm.out.log
```

#### エラーログの確認
```bash
tail -f cron_logs/lineworks_cred_llm.err.log
```

#### 過去のログを検索
```bash
grep "ERROR" cron_logs/lineworks_cred_llm.err.log
grep "送信完了" cron_logs/lineworks_cred_llm.out.log
```

### 6. デバッグモード

#### dry-runでテスト
```bash
python src/lineworks_cred_llm.py --dry-run
```

#### 詳細ログを有効にする
```python
# src/lineworks_cred_llm.py の30行目を変更
logging.basicConfig(level=logging.DEBUG,  # INFOからDEBUGに変更
                    format="%(asctime)s [%(levelname)s] %(message)s")
```

### 7. 完全リセット手順

問題が解決しない場合の完全リセット：

```bash
# 1. 古いサービスを停止
launchctl unload ~/Library/LaunchAgents/com.gen.lineworks.cred.llm.plist

# 2. 依存関係を再インストール
pip uninstall -y selenium python-dotenv jpholiday
pip install -r requirements.txt

# 3. ChromeDriverを再インストール
brew uninstall chromedriver
brew install chromedriver

# 4. 設定ファイルを再作成
cp .env.example .env
# .envファイルを編集

# 5. サービスを再開
launchctl load ~/Library/LaunchAgents/com.gen.lineworks.cred.llm.plist

# 6. テスト実行
python src/lineworks_cred_llm.py --dry-run
```

### 8. サポート情報

問題が解決しない場合は、以下の情報を含めて報告してください：

1. macOSのバージョン
2. Pythonのバージョン
3. Chromeのバージョン
4. ChromeDriverのバージョン
5. エラーログの内容
6. 実行時の環境（手動実行 or 自動実行）

```bash
# システム情報の収集
echo "macOS: $(sw_vers -productVersion)"
echo "Python: $(python --version)"
echo "Chrome: $(/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version)"
echo "ChromeDriver: $(chromedriver --version)"
```