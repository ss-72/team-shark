# Scrum Board Application

このプロジェクトは、スクラム管理用のWebアプリケーションです。

## 技術スタック

- **フロントエンド**: HTML/CSS/JavaScript
- **バックエンド**: Python/Flask
- **実行環境**: AWS Elastic Beanstalk
- **データベース**: Amazon RDS (MySQL/PostgreSQL)
- **ファイル保存**: Amazon S3
- **開発管理**: Git/GitHub

## ディレクトリ構成

```
scrum/
├── backend/              # Flaskバックエンド
│   ├── routes/          # APIエンドポイント
│   ├── models/          # データベースモデル
│   ├── services/        # ビジネスロジック
│   ├── utils/           # ユーティリティ関数
│   ├── tests/           # テストコード
│   ├── app.py           # メインアプリケーション
│   ├── config.py        # 設定ファイル
│   ├── requirements.txt  # Python依存関係
│   └── .env.example     # 環境変数テンプレート
├── frontend/            # フロントエンド
│   ├── css/             # スタイルシート
│   ├── js/              # JavaScriptコード
│   ├── images/          # 画像ファイル
│   ├── pages/           # HTMLページ
│   └── index.html       # メインページ
├── .ebextensions/       # AWS Elastic Beanstalk設定
├── infra/               # インフラストラクチャコード (IaC)
├── docs/                # ドキュメント
├── .gitignore           # Git除外ファイル
└── README.md            # このファイル
```

## セットアップ手順

### バックエンド

1. Python仮想環境を作成
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
```

2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

3. 環境変数を設定
```bash
copy .env.example .env
# .envファイルを編集して、実際の値を設定
```

4. アプリケーションを起動
```bash
python app.py
```

### フロントエンド

静的ファイルはそのままブラウザから開くか、開発サーバーで提供できます。

## デプロイ

### AWS Elastic Beanstalk

```bash
eb init -p python-3.11 scrum-app
eb create scrum-env
eb deploy
```

## 開発ワークフロー

1. フィーチャーブランチを作成
```bash
git checkout -b feature/new-feature
```

2. コードを実装

3. コミットしてプッシュ
```bash
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

4. プルリクエストを作成

## トラブルシューティング

- ポート5000が既に使用されている場合: `python app.py --port 5001`
- データベース接続エラー: `.env`ファイルのDATABASE_URLを確認
