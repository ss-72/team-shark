# スプリント2 軌道修正計画書

> **作成日**: 2026/7/21
> **対象**: 要件軌道修正に伴う再計画（チーム5人）
> **プロジェクト**: 学校向け時間割・教室自動割り当てシステム

---

## 1. 経緯と目的

スプリント1では教員CRUD・教室CRUD・時間枠CRUD・自動生成コアエンジンを完了した。
しかし、実際の現場ニーズを踏まえ、以下の要求が新たに発生したため、スプリント2で軌道修正を行う。

### 教員からの要求（抜粋）
> 「この曜日はだめ」「この曜日の何時間目はNG」みたいなのも
> 自分に割り当てられた教室を表示
> 科目ごとの決められたコマ数もしっかり満たせるように

### 受入条件の変化

| # | 旧要件 | 新要件 | インパクト |
|---|--------|--------|-----------|
| 1 | 管理者だけが教員情報を管理 | **ユーザ管理（教員ログイン）＋自分に割り当てられた教室を表で表示** | 🔴 大: ログイン機構＋個人向けビューが必要 |
| 2 | 教員の希望入力（科目・コマ数）は次スプリント | **科目ごとの必要コマ数を確実に満たす** | 🟡 中: モデル拡張＋生成ロジック強化 |
| 3 | 教員の希望入力（勤務可能日時）は次スプリント | **曜日単位・時限単位の出勤不可設定** | 🟡 中: 新モデル＋生成ロジック制約追加 |
| 4 | 教員向け時間割表示UIは次スプリント | **自分に割り当てられた教室表示を優先実装** | 🟡 中: シンプルな個人表示画面 |

---

## 2. 新要件の全体像

```
┌─────────────────────────────────────────────────┐
│                 時間割・教室管理システム                          │
├─────────────────────────────────────────────────┤
│                                                   │
│  【既存・変更なし】         【新規・軌道修正】                │
│  ┌─────────────────┐   ┌─────────────────────────┐│
│  │ 教員CRUD         │   │ ユーザ管理（ログイン）      ││
│  │ 教室CRUD         │   │ 教員個人の出勤不可設定      ││
│  │ 時間枠CRUD       │   │  ・曜日単位NG              ││
│  │ 時間割CRUD       │   │  ・時限単位NG              ││
│  │ 自動生成エンジン  │   │ 科目ごとの必要コマ数管理      ││
│  │ 週間カレンダー表示│   │ 個人別「自分の教室」表示     ││
│  └─────────────────┘   │ 生成ロジック制約対応          ││
│                         └─────────────────────────┘│
└─────────────────────────────────────────────────┘
```

---

## 3. 新規追加・改修が必要なコンポーネント一覧

### 3.1 データモデル変更

| モデル | 変更内容 | 変更種別 |
|--------|---------|----------|
| `Teacher` | `required_periods`（必要コマ数, Integer）フィールド追加 | カラム追加 |
| `Teacher` | `password_hash`（ログイン用パスワード, String）フィールド追加 | カラム追加 |
| **新規: `TeacherUnavailability`** | 教員の出勤不可日時を管理するテーブル | 新規モデル |

#### TeacherUnavailability モデル設計案

```python
class TeacherUnavailability(db.Model):
    __tablename__ = 'teacher_unavailabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)  # 'Monday'～'Friday'
    period = db.Column(db.Integer, nullable=True)  # None=曜日全体NG, 1-5=特定時限NG
    
    teacher = db.relationship('Teacher', backref='unavailabilities')
    
    __table_args__ = (
        UniqueConstraint('teacher_id', 'day_of_week', 'period', name='u_teacher_unavail'),
    )
```

### 3.2 APIエンドポイント変更

| エンドポイント | メソッド | 変更内容 |
|---------------|---------|----------|
| `/api/teachers/<id>` | PUT | `required_periods`、`password_hash` 更新対応 |
| `/api/teachers/<id>` | GET | 同上レスポンス対応 |
| **新規: `/api/auth/login`** | POST | 教員ログイン認証 |
| **新規: `/api/auth/me`** | GET | ログイン中の教員情報取得 |
| **新規: `/api/teachers/<id>/unavailabilities`** | CRUD | 出勤不可設定の管理 |
| `/api/timetables/generate` | POST | 出勤不可・必要コマ数考慮ロジックに変更 |
| **新規: `/api/timetables/my`** | GET | ログイン教員の時間割（自分の教室一覧）取得 |

### 3.3 フロントエンド新規画面

| 画面 | URL | 説明 |
|------|-----|------|
| **ログインページ** | `/frontend/pages/login.html` | 教員ID＋パスワード認証 |
| **マイ時間割ページ** | `/frontend/pages/my_timetable.html` | 自分に割り当てられた教室を表形式で表示 |
| **出勤不可設定ページ** | `/frontend/pages/my_availability.html` | 自分が出勤できない曜日・時限を設定 |

### 3.4 既存画面への追加

| 画面 | 追加内容 |
|------|---------|
| 教員管理画面 (`teachers.html`) | `required_periods` 入力フィールド追加 |

---

## 4. 自動生成エンジンへの影響

現在の `timetable_generator.py` は「全教員を均等にスロットに割り当てる」だけの単純ロジック。
以下の強化が必要。

### 4.1 追加すべき制約

| # | 制約 | 優先度 | 説明 |
|---|------|--------|------|
| 1 | **コマ数保証** | 🔴 必須 | 教員ごとに `required_periods` で指定されたコマ数を確実に割り当てる |
| 2 | **出勤不可曜日** | 🔴 必須 | 曜日全体NGの日は割り当てない |
| 3 | **出勤不可時限** | 🟡 必須 | 特定曜日＋時限がNGの場合は割り当てない |
| 4 | **既存制約維持** | 🔴 必須 | 教員重複・教室重複・非常勤優先・オンライン均等化は引き続き維持 |

### 4.2 改修イメージ

```python
def generate_timetable():
    """時間割を自動生成（制約対応版）"""
    
    # 1. 既存の時間割をクリア
    Timetable.query.delete()
    
    # 2. 教員一覧を取得（非常勤→常勤の順）
    teachers = Teacher.query.all()
    teachers.sort(key=lambda t: 0 if t.employment_type == "非常勤" else 1)
    
    # 3. 出勤不可マップを事前構築
    #    unavail_map[(teacher_id, day, period)] = True でNG
    unavail_map = {}
    for u in TeacherUnavailability.query.all():
        if u.period is None:
            # 曜日全体NG → 全時限をマーク
            for p in PERIODS:
                unavail_map[(u.teacher_id, u.day_of_week, p)] = True
        else:
            unavail_map[(u.teacher_id, u.day_of_week, u.period)] = True
    
    # 4. 教員ごとに必要コマ数を満たすよう割り当て
    #    各教員に required_periods 分のスロットを確保するまでループ
    
    # 5. 使用済みスロット管理
    used_teacher_slots = set()
    used_classroom_slots = set()
    
    # 6. コマ数保証：各教員に必要コマ数を割り当て
    assignments = {t.id: 0 for t in teachers}
    
    for teacher in teachers:
        target = teacher.required_periods or 5  # デフォルト5コマ
        while assignments[teacher.id] < target:
            # 空きスロットを探して割り当て
            # 出勤不可チェック → 重複チェック → 教室割り当て
            ...
    
    # 7. 残りスロットを均等に割り当て（余力があれば）
    ...
```

---

## 5. チーム分割と担当

### チーム構成（5人）

| チーム | メンバー | 主担当領域 |
|--------|---------|-----------|
| **チームA** | 2人 | ユーザ管理・ログイン・フロントエンド |
| **チームB** | 2人 | 出勤不可管理・モデル変更・API |
| **チームC** | 1人 | 自動生成エンジン改修（制約対応） |

### 5.1 チームA：ユーザ管理・ログイン・マイ時間割表示（2人）

| # | タスク | 担当ファイル | 工数目安 |
|---|--------|-------------|---------|
| A1 | ログインページ作成（HTML） | `frontend/pages/login.html`（新規） | 0.5日 |
| A2 | ログイン処理JS実装 | `frontend/js/login.js`（新規） | 0.5日 |
| A3 | 認証API実装（ログイン・セッション） | `backend/routes/auth.py`（新規） | 1日 |
| A4 | 「マイ時間割」ページ作成 | `frontend/pages/my_timetable.html`（新規） | 1日 |
| A5 | 「マイ時間割」JS実装（自分の教室一覧表） | `frontend/js/my_timetable.js`（新規） | 1日 |
| A6 | 教員管理画面に `required_periods` 追加 | `frontend/pages/teachers.html`, `frontend/js/teachers.js` | 0.5日 |
| A7 | 出勤不可設定画面作成 | `frontend/pages/my_availability.html`（新規） | 1日 |
| A8 | 出勤不可設定JS実装 | `frontend/js/my_availability.js`（新規） | 0.5日 |

**チームA 合計工数: 約6日**

### 5.2 チームB：モデル変更・API・出勤不可管理（2人）

| # | タスク | 担当ファイル | 工数目安 |
|---|--------|-------------|---------|
| B1 | Teacherモデルに `required_periods` 追加 | `backend/models/teacher.py` | 0.5日 |
| B2 | Teacherモデルに `password_hash` 追加 | `backend/models/teacher.py` | 0.5日 |
| B3 | TeacherUnavailabilityモデル新規作成 | `backend/models/unavailability.py`（新規） | 0.5日 |
| B4 | 教員APIに `required_periods` 対応 | `backend/routes/teachers.py` | 0.5日 |
| B5 | 出勤不可CRUD API実装 | `backend/routes/unavailabilities.py`（新規） | 1日 |
| B6 | マイ時間割API実装（`/api/timetables/my`） | `backend/routes/timetables.py` | 1日 |
| B7 | 認証API実装サポート（トークン or セッション） | `backend/routes/auth.py`（チームAと協力） | 0.5日 |
| B8 | シーダー更新（seed教員にrequired_periods含める） | `backend/app.py` | 0.5日 |
| B9 | DB migration（新テーブル作成） | 自動（`db.create_all()`） | 0.5日 |

**チームB 合計工数: 約5.5日**

### 5.3 チームC：自動生成エンジン改修（1人）

| # | タスク | 担当ファイル | 工数目安 |
|---|--------|-------------|---------|
| C1 | 出勤不可制約を生成ロジックに追加 | `backend/services/timetable_generator.py` | 1.5日 |
| C2 | 必要コマ数保証ロジック追加 | `backend/services/timetable_generator.py` | 1.5日 |
| C3 | 既存制約（非常勤優先・重複回避）維持確認 | `backend/services/timetable_generator.py` | 0.5日 |
| C4 | 自動生成APIテスト更新 | `backend/tests/test_api.py` | 1日 |
| C5 | エッジケースのテスト追加 | `backend/tests/test_api.py` | 0.5日 |

**チームC 合計工数: 約5日**

---

## 6. スケジュール（2週間 = 10営業日）

```
Week 1 (月〜金)
 ┌──────┬──────┬──────┬──────┬──────┐
 │ 月   │ 火   │ 水   │ 木   │ 金   │
├──────┼──────┼──────┼──────┼──────┤
 │A     │A     │A     │A     │A     │
 │ログイン    │ログイン    │マイ時間割   │マイ時間割   │出勤不可設定  │
 │ペー  │API   │ペー  │JS    │画面   │
 │ジ    │      │ジ    │      │      │
├──────┼──────┼──────┼──────┼──────┤
 │B     │B     │B     │B     │B     │
 │モデル     │出勤不可     │出勤不可     │マイ時間割   │認証＋      │
 │変更  │CRUD  │API完成    │API   │結合    │
├──────┼──────┼──────┼──────┼──────┤
 │C     │C     │C     │C     │C     │
 │現状分析     │出勤不可     │コマ数      │結合テスト   │テスト     │
 │＋設計 │制約実装     │保証実装     │      │      │
 └──────┴──────┴──────┴──────┴──────┘

Week 2 (月〜金)
 ┌──────┬──────┬──────┬──────┬──────┐
 │ 月   │ 火   │ 水   │ 木   │ 金   │
├──────┼──────┼──────┼──────┼──────┤
 │A     │A     │A     │全チーム    │全チーム    │
 │結合修正     │結合修正     │最終調整     │結合テスト   │完了確認    │
 │      │      │      │＋修正  │＋レビュー   │
├──────┼──────┼──────┼──────┼──────┤
 │B     │B     │B     │      │      │
 │結合修正     │結合修正     │最終調整     │      │      │
├──────┼──────┼──────┼──────┼──────┤
 │C     │C     │C     │      │      │
 │生成ロジック   │エッジ     │最終調整     │      │      │
 │最終調整     │ケース追加     │      │      │      │
 └──────┴──────┴──────┴──────┴──────┘
```

---

## 7. 完了条件（新）

1. ✅ 教員が自身のID＋パスワードでログインできる
2. ✅ ログイン後、自分に割り当てられた教室が「曜日×時限」の表形式で表示される
3. ✅ 教員が「この曜日は出勤不可」「この曜日の○時限は出勤不可」を設定できる
4. ✅ 出勤不可設定が自動生成に反映される（設定した時間に割り当てられない）
5. ✅ 科目ごとの必要コマ数（required_periods）が自動生成で満たされる
6. ✅ 既存機能（教員重複なし・教室重複なし・非常勤優先・オンライン均等化）は維持

---

## 8. リスクと対策

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| セッション管理の複雑化 | 🟡 中 | 🟡 中 | まずはシンプルなトークン認証で始める |
| 生成ロジックの制約増加によるパフォーマンス悪化 | 🟢 低 | 🟡 中 | 教員数が少ない現状では問題にならない想定 |
| フロントエンドの変更範囲が大きい | 🟡 中 | 🟡 中 | チームAの2人で分担（1人ログイン、1人マイ時間割） |
| DBスキーマ変更による既存データの互換性 | 🟢 低 | 🟢 低 | SQLite開発環境では再作成が容易 |

---

## 9. アーキテクチャ（変更後）

```
フロントエンド (HTML + JS)
  │ HTTP (fetch API)
  ▼
Flask Backend (Blueprint)
  ├─ /api/auth              → auth.py (新規)
  │   ├─ POST /login        → ログイン認証
  │   └─ GET /me            → 現在のユーザ情報
  ├─ /api/teachers          → teachers.py (改修)
  │   └─ required_periods / password_hash 対応
  ├─ /api/teachers/<id>/unavailabilities → unavailabilities.py (新規)
  ├─ /api/classrooms        → classrooms.py (変更なし)
  ├─ /api/time_slots        → time_slots.py (変更なし)
  └─ /api/timetables        → timetables.py (改修)
      ├─ GET /my            → ログインユーザの時間割 (新規)
      ├─ POST /generate     → 制約対応版生成 (改修)
      └─ ... (既存CRUD維持)
  │
  ▼
SQLAlchemy ORM → SQLite (開発) / MySQL (本番想定)

データモデル追加:
  ┌──────────┐     ┌────────────────────┐
  │ Teacher   │────→│ TeacherUnavailability │
  │          │1:N  │                    │
  │required_  │     │teacher_id          │
  │periods   │     │day_of_week         │
  │password_  │     │period (nullable)   │
  │hash      │     └────────────────────┘
  └──────────┘
```

---

## 10. チームへの指示事項

### チームAへの指示

1. **ログインページ**はシンプルに。教員名 or ID＋パスワードのフォームのみ。
2. **トークン認証**を採用。ログイン成功時にトークンを発行し、localStorageに保存。
3. **マイ時間割**は「行＝時限（1〜5）、列＝曜日（月〜金）」のテーブル。セルには「教室名」を表示。空きコマは「-」。
4. デザインは既存の `style.css` に追従。新規CSSは最小限。
5. 出勤不可設定画面は、チェックボックス形式で各曜日×時限をON/OFF。
6. チームBと連携して認証APIの仕様を合わせること。

### チームBへの指示

1. **TeacherUnavailabilityモデル**は別ファイル `models/unavailability.py` に作成。
2. **`required_periods`** のデフォルト値は `5`（週5コマ想定）。
3. **`password_hash`** は `werkzeug.security.generate_password_hash` を使用。
4. **認証API**は簡易トークン方式。`auth.py` に `login()` と `me()` を実装。
5. トークンは `secrets.token_hex(16)` で生成し、メモリ上の辞書で保持（本番はRedis等に変更可能）。
6. 出勤不可APIは教師IDをURLパラメータで受け取る：
   - `GET /api/teachers/<id>/unavailabilities` - 一覧取得
   - `POST /api/teachers/<id>/unavailabilities` - 作成
   - `DELETE /api/teachers/<id>/unavailabilities/<uid>` - 削除
7. チームCと協力して、出勤不可データのフォーマットを合わせること。

### チームCへの指示

1. **生成ロジックの流れ**を以下の順に変更：
   a. 出勤不可マップを事前構築
   b. 教員を必要コマ数順（多い順）にソート
   c. 各教員に必要コマ数割り当て（出勤不可をスキップ）
   d. 非常勤優先は維持（必要コマ数割り当て時は非常勤を先に）
   e. 残りスロットを均等に割り当て
   f. オンライン均等化は最後に実行
2. **既存の重複回避ロジック**はそのまま維持。
3. **無限ループ対策**：必要コマ数が空きスロット数より多い場合は、割り当て可能な最大数で諦める。
4. テストパターン：
   - 出勤不可設定が反映されること
   - 必要コマ数が満たされること（教員1人／複数人）
   - 空きスロット不足時にエラーにならないこと
   - 既存の重複チェックが機能すること