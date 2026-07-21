# スプリント1 進捗サマリー

> **作成日**: 2026/7/21
> **対象**: 学校向け時間割・教室自動割り当てシステム（PBI: BI001〜BI021）

---

## 全体進捗

| 項目 | 進捗 |
|------|------|
| スプリント完了タスク | **約 90%** |
| 完了条件3項目 | ✅ 全て達成 |

---

## 完了したPBI（プロダクトバックログ項目）

| PBI | 内容 | 状態 | 備考 |
|-----|------|------|------|
| BI008 | 教員情報管理（CRUD + バリデーション） | ✅ 完了 | 名前重複チェック、空文字チェック実装済み |
| BI009 | 教室・時間枠・基本TT（CRUD + バリデーション） | ✅ 完了 | 同名重複チェック、時限重複チェック、時間帯重複チェック実装済み |
| BI012 | 自動割り当てコアエンジン | ✅ 完了 | `services/timetable_generator.py` 実装済み |
| BI013 | 非常勤講師優先ルール | ✅ 完了 | コアエンジンに包含 |
| BI015 | オンライン授業均等化 | ✅ 完了 | コアエンジンに包含 |

---

## 完了条件の達成状況

| # | 完了条件 | 状態 | 説明 |
|---|---------|------|------|
| 1 | 各CRUDが適切なバリデーション付きで動作 | ✅ | 教員・教室・時間枠・時間割すべてにバリデーション実装済み |
| 2 | 「自動生成」ボタンで重複なし時間割生成 | ✅ | `POST /api/timetables/generate` エンドポイント実装済み |
| 3 | 生成結果が週間カレンダー形式で表示される | ✅ | 行=時限・列=曜日のテーブル形式、フィルタ機能付き |

---

## 実装ファイル一覧

### チームA：マスターデータ管理

| ファイル | 種別 | 状態 |
|---------|------|------|
| `backend/routes/teachers.py` | BE | ✅ CRUD＋バリデーション実装済み |
| `backend/routes/classrooms.py` | BE | ✅ CRUD＋バリデーション実装済み |
| `backend/routes/time_slots.py` | BE | ✅ CRUD＋バリデーション実装済み |
| `backend/models/teacher.py` | BE | ✅ 変更不要 |
| `backend/models/classroom.py` | BE | ✅ 変更不要 |
| `backend/models/time_slot.py` | BE | ✅ 変更不要 |
| `frontend/pages/teachers.html` | FE | ✅ 動作済み |
| `frontend/pages/classrooms.html` | FE | ✅ 動作済み |
| `frontend/pages/time_slots.html` | FE | ✅ 動作済み |
| `frontend/js/teachers.js` | FE | ✅ 動作済み |
| `frontend/js/classrooms.js` | FE | ✅ 動作済み |
| `frontend/js/time_slots.js` | FE | ✅ 動作済み |
| `frontend/css/style.css` | FE | ✅ 動作済み |
| `backend/requirements.txt` | 共通 | ✅ Flask-Cors追記、バージョン固定済み |

### チームB：時間割コア機能

| ファイル | 種別 | 状態 |
|---------|------|------|
| `backend/routes/timetables.py` | BE | ✅ CRUD＋重複チェック実装済み |
| `backend/models/timetable.py` | BE | ✅ `find_conflicts` 実装済み |
| `backend/services/timetable_generator.py` | BE | ✅ 自動生成エンジン実装済み |
| `backend/app.py` | BE | ⚠️ DB設定要修正（MySQL参照のまま） |
| `frontend/pages/timetables.html` | FE | ✅ 自動生成ボタン＋カレンダーセクション追加済み |
| `frontend/js/timetables.js` | FE | ✅ 自動生成呼び出し追加済み |
| `frontend/js/timetable_view.js` | FE | ✅ 週間カレンダー表示実装済み |

### テスト

| ファイル | 状態 |
|---------|------|
| `backend/tests/test_api.py` | ⚠️ 正常系テスト＋自動生成テストは実装済み。エラー系テストは未充足 |

---

## 残タスク一覧

| # | タスク | 担当 | 優先度 | 状態 | 備考 |
|---|--------|------|--------|------|------|
| 1 | app.py の DB 接続設定の見直し | 共通 | 🔴 致命的 | ❌ 未対応 | 現状 `mysql+pymysql://` ハードコード。環境変数化 or SQLite対応推奨 |
| 2 | トースト通知（成功/エラー）の実装 | チームA | 🟡 推奨 | ⚠️ 部分完了 | フォーム内エラー表示は実装済み。トーストUI未実装 |
| 3 | エラー系テストの追加 | チームA | 🟢 任意 | ❌ 未対応 | バリデーションエラー、重複エラー、404等のテストケース |
| 4 | 自動生成APIのエッジケーステスト | チームB | 🟢 任意 | ❌ 未対応 | データ不足時の動作など |

---

## やらないこと（次スプリント以降）

| PBI | 内容 |
|-----|------|
| BI006 | AWS環境準備（Terraform） |
| BI007 | ツール習得 |
| BI010 | 教員の希望入力 |
| BI011 | 未入力教員リマインド |
| BI014 | 学科優先教室・移動考慮 |
| BI016 | 教員向け時間割表示UI |
| BI017 | 手動調整 |
| BI018 | ログイン機能 |

---

## アーキテクチャ概要

```
フロントエンド (HTML + JS)
  │ HTTP (fetch API)
  ▼
Flask Backend (Blueprint)
  ├─ /api/teachers      → teachers.py
  ├─ /api/classrooms    → classrooms.py
  ├─ /api/time_slots    → time_slots.py
  └─ /api/timetables    → timetables.py
        └─ /generate    → timetable_generator.py
  │
  ▼
SQLAlchemy ORM → SQLite (開発) / MySQL (本番想定)
```

### 自動生成エンジンの処理フロー

1. 既存の時間割を全削除
2. 教員一覧を取得（非常勤→常勤の順にソート）
3. 教室一覧を取得
4. 使用済みスロットを管理しながら各教員に空き枠を割り当て
5. 割り当て後、オンライン授業を均等に分散マーク