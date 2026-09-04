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

通常起動時は、ログインに必要な管理者アカウント以外のデータを作成しません。サンプルデータが必要な場合だけ `SEED_DEMO_DATA=true` を設定して起動してください。`TESTING=True` で `create_app()` を呼び出すテストではseedを投入せず、各テストが必要なデータを明示的に作成します。

テストは次のコマンドで実行します。

```bash
cd backend
python -m unittest discover -s tests
```

## 初期管理者アカウント（重要）

本アプリケーションは起動時に初期管理者（admin）を自動で作成しますが、セキュリティ上の理由から管理者アカウントのユーザー名とパスワードは必ず環境変数で明示的に指定してください。指定がない場合、非テスト起動は例外となり起動が中止されます。

必須環境変数:

- `ADMIN_USERNAME` — 初期管理者のユーザー名
- `ADMIN_PASSWORD` — 初期管理者のパスワード

起動例（PowerShell）:

```powershell
$env:ADMIN_USERNAME='admin'
$env:ADMIN_PASSWORD='secure-password'
python backend/app.py
```

パスワードはログやリポジトリに書かないでください。運用時は安全なシークレット管理（Vault、CI/CDのシークレット、環境設定）を利用してください。


## DBスキーマ変更方針

現在は Flask-SQLAlchemy の `db.create_all()` を使用しています。これは新規テーブルを作成できますが、既存テーブルへ安全に列を追加・変更するマイグレーションではありません。

開発環境で `User`、`Subject`、`TeacherSubject`、`TeacherUnavailability`、または `Timetable.subject_id` を追加する際は、既存データを保持する必要がないことを確認した上で、開発用DBを削除してからアプリを再起動し、スキーマを作り直します。本番データや保持すべき共有データではこの方法を使わず、導入判断をしたマイグレーション手段で適用します。

## プロジェクト共通データ契約

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

- 必要コマ数の正は `Subject.required_periods_per_week` です。値はコマ数で、`1時限 = 2コマ` として時間割を生成します。そのため必要コマ数は2以上の偶数にします。`Teacher.required_periods` は作成しません。
- `TeacherSubject` は教員が担当可能な科目を表します。
- `TeacherUnavailability.period` が `NULL` の場合は終日不可、数値の場合はその時限のみ不可です。
- 曜日は `Monday`、`Tuesday`、`Wednesday`、`Thursday`、`Friday` を使用します。
