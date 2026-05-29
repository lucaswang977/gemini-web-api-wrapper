FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# メインスクリプトのコピー
COPY main.py .

# アプリケーションの実行コマンド
CMD ["python", "main.py"]
