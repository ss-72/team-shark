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

## テストと開発用seed

開発起動時は、教員・教室・時間枠のサンプルデータを自動作成します。一方、`TESTING=True` で `create_app()` を呼び出すテストでは開発用seedを投入しません。各テストで必要なデータを明示的に作成してください。

テストは次のコマンドで実行します。

```bash
cd backend
python -m unittest discover -s tests
```

## DBスキーマ変更方針

現在は Flask-SQLAlchemy の `db.create_all()` を使用しています。これは新規テーブルを作成できますが、既存テーブルへ安全に列を追加・変更するマイグレーションではありません。

開発環境で `User`、`Subject`、`TeacherSubject`、`TeacherUnavailability`、または `Timetable.subject_id` を追加する際は、既存データを保持する必要がないことを確認した上で、開発用DBを削除してからアプリを再起動し、スキーマを作り直します。本番データや保持すべき共有データではこの方法を使わず、導入判断をしたマイグレーション手段で適用します。

## チームA共通データ契約

後続のA-1/A-2とチームBは次の名前を共通契約として使用します。

```text
User.teacher_id

Subject.id
Subject.name
Subject.required_periods_per_week

TeacherSubject.teacher_id
TeacherSubject.subject_id

TeacherUnavailability.teacher_id
TeacherUnavailability.day_of_week
TeacherUnavailability.period

Timetable.subject_id
```

- 必要コマ数の正は `Subject.required_periods_per_week` です。`Teacher.required_periods` は作成しません。
- `TeacherSubject` は教員が担当可能な科目を表します。
- `TeacherUnavailability.period` が `NULL` の場合は終日不可、数値の場合はその時限のみ不可です。
- 曜日は `Monday`、`Tuesday`、`Wednesday`、`Thursday`、`Friday` を使用します。
