# チームA 実装指示書
## 基盤・認証・管理機能チーム

> 更新日: 2026-08-25  
> 上位仕様: `docs/PROJECT_PLAN.md`  
> この文書はチームAの担当範囲・実装順序・完了条件を定義する。仕様が衝突した場合は必ず `PROJECT_PLAN.md` を優先する。

---

## 0. 生成AIに渡すときの前提

生成AIには最低限、次を読ませる。

- `docs/PROJECT_PLAN.md`
- `docs/TEAM_A.md`
- 実際に変更する周辺ソースコード

`docs/archive/` は旧仕様であり、現行仕様の根拠にはしない。

Git運用方法はこの文書では扱わない。

---

# 1. チームAの目的

チームAは、**チームBが自動生成と教員向け機能を実装できる土台を完成させる**。

担当領域:

1. DB・データモデル
2. ログイン・認証・権限
3. 科目・担当科目・出勤不可条件の管理API
4. 管理者向けUI
5. 既存テスト・seedの整理

5人を2チームに分ける場合、チームAは3人を想定する。

---

# 2. A-1 基盤・認証担当

## 主担当

- `User` モデル
- 認証
- 権限制御
- DB変更の土台
- `backend/app.py` への登録
- TESTING時のseed整理

主な変更候補:

```text
backend/models/user.py
backend/routes/auth.py
backend/routes/users.py
backend/app.py
backend/tests/
```

## User仕様

```text
User
- id
- username
- password_hash
- role
- teacher_id
- is_active
```

必須:

- `username` は一意
- パスワード平文保存禁止
- roleは `admin` / `teacher`
- teacherユーザーはTeacherと紐付く
- 無効ユーザーはログイン不可

## 認証API

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

認証方式はHTTP-onlyセッションCookieを基本とする。

## 権限

- 管理API: adminのみ
- 本人向けAPI: ログイン済みteacher
- 未認証: 401
- 権限不足: 403

## 完了条件

- 管理者・教員でログインできる
- logoutできる
- `/api/auth/me` で現在ユーザーが分かる
- teacherが管理APIを実行できない
- パスワードが平文保存されていない

---

# 3. A-2 科目・制約データ/API担当

## 主担当

- `Subject`
- `TeacherSubject`
- `TeacherUnavailability`
- `Timetable.subject_id`
- 管理API

主な変更候補:

```text
backend/models/subject.py
backend/models/teacher_subject.py
backend/models/teacher_unavailability.py
backend/models/timetable.py
backend/routes/subjects.py
backend/routes/teachers.py
backend/routes/timetables.py
backend/tests/
```

## Subject

```text
Subject
- id
- name
- required_periods_per_week
```

必須:

- `name` 一意
- `required_periods_per_week >= 1`
- 科目ごとの必要コマ数はここを正とする
- `Teacher.required_periods` は新設しない

## TeacherSubject

```text
TeacherSubject
- teacher_id
- subject_id
```

- 同一組み合わせの重複禁止
- 自動生成では登録された担当可能教員のみ候補

## TeacherUnavailability

```text
TeacherUnavailability
- id
- teacher_id
- day_of_week
- period
```

意味:

```text
Tuesday / NULL -> 火曜終日NG
Thursday / 3   -> 木曜3限NG
```

- 曜日: `Monday` ～ `Friday`
- `period = NULL`: 終日不可
- 数値: 特定時限不可
- 同一条件重複禁止

## Timetable

既存モデルに:

```text
subject_id
```

を追加する。

## 管理API

最低限:

```text
/api/subjects
/api/teachers/<id>/subjects
/api/teachers/<id>/unavailable-slots
```

## 手動時間割登録の検証

可能な範囲でPOST/PUT時にも:

- subject存在
- teacherがsubjectを担当可能
- teacherの不可日時ではない
- teacher重複なし
- classroom重複なし

を確認する。

## 完了条件

- 科目と必要コマ数をCRUDできる
- 教員に担当科目を設定できる
- 曜日NG・時限NGを設定できる
- Timetableにsubjectを保存できる
- 不正値に適切な4xxを返す

---

# 4. A-3 管理UI・基盤テスト担当

## 主担当

管理者がブラウザから必要データを準備できる状態にする。

必要画面:

1. 科目管理
2. 科目ごとの必要コマ数設定
3. 教員の担当可能科目設定
4. 教員の出勤不可設定
5. 必要ならユーザー管理

既存HTML/CSS/JavaScriptをできるだけ再利用する。

複雑なUIより、確実に操作できることを優先する。

## テスト基盤

目標:

```bash
python -m unittest discover -s backend/tests
```

既存seedとテストの古い前提を整理する。

推奨:

- TESTING時は自動seedを無効化
- テストごとに必要データを明示投入

## 最低限のテスト

- 重複username
- 不正ログイン
- teacherによるadmin APIアクセス
- required_periods_per_week = 0
- 存在しないteacher/subject
- TeacherSubject重複
- TeacherUnavailability重複

---

# 5. チームAの実装順序

## Step 1
既存コード確認:

```text
backend/app.py
backend/models/
backend/routes/
backend/tests/
```

## Step 2
DB変更方針を決める。

`db.create_all()` だけでは既存テーブルへ安全にカラム追加できない。

- 開発DBを再作成する
- またはマイグレーションを導入する

どちらを採用したか記録する。

## Step 3
モデル完成:

- User
- Subject
- TeacherSubject
- TeacherUnavailability
- Timetable.subject_id

## Step 4
認証・管理API

## Step 5
管理UI

## Step 6
テスト

---

# 6. チームBへ早めに渡す契約

## モデル

```text
Subject.id
Subject.name
Subject.required_periods_per_week

TeacherSubject.teacher_id
TeacherSubject.subject_id

TeacherUnavailability.teacher_id
TeacherUnavailability.day_of_week
TeacherUnavailability.period

Timetable.teacher_id
Timetable.subject_id
Timetable.classroom_id
Timetable.day_of_week
Timetable.period
```

## 認証

```text
GET /api/auth/me
```

ログインteacherに対応する `teacher_id` をサーバー側で判定できること。

## 生成器から利用できる情報

- 全科目と必要コマ数
- 各科目の担当可能教員
- 各教員の不可日時
- 全教室
- 使用可能な曜日・時限

---

# 7. チームAが原則触らない領域

チームB主担当:

```text
backend/services/timetable_generator.py
GET /api/my/timetable
教員本人向け時間割画面
自動生成アルゴリズム
生成失敗理由の計算
```

必要な場合は担当を確認してから変更する。

---

# 8. 今日の優先順位

## 最優先

- [ ] 既存テスト・seed整理
- [ ] User
- [ ] Subject
- [ ] TeacherSubject
- [ ] TeacherUnavailability
- [ ] Timetable.subject_id

## 次

- [ ] 認証API
- [ ] 科目API
- [ ] 担当科目API
- [ ] 不可条件API

## 余裕があれば

- [ ] 管理UI
- [ ] User管理UI
- [ ] 手動時間割の新制約チェック

---

# 9. Definition of Done

- [ ] 新モデルがDB上で正常利用できる
- [ ] 管理APIから操作できる
- [ ] ログイン・権限制御が機能する
- [ ] 管理者が必要データを準備できる
- [ ] チームBがモデルを推測せず利用できる
- [ ] テストが成功する
- [ ] 既存CRUDが致命的に壊れていない

---

# 10. 生成AI向け作業開始指示

以下をそのままAIへの冒頭指示として使用できる。

```text
あなたは「時間割・教室自動割り当てシステム」のチームA担当開発者です。

最上位仕様は docs/PROJECT_PLAN.md、
担当範囲は docs/TEAM_A.md です。

最初に両方を読み、その後、担当する既存コードを確認してください。
docs/archive/ は旧仕様なので現行仕様の根拠として使用しないでください。

チームAの目的は、
1. データモデル
2. 認証・権限
3. 管理API
4. 管理者UI
を完成させ、チームBが自動生成と教員向け機能を実装できる土台を提供することです。

既存コードを確認せず全面書き換えしないでください。
担当外の timetable_generator.py を大幅変更しないでください。
API名・モデル名を独自判断で変更しないでください。

作業前に、
- 現在実装済みのもの
- 今回変更するファイル
- 実装順序
を短く整理してください。

実装後はテストを実行し、
- 完了項目
- 未完了項目
- 既知の問題
- チームBへ共有するAPI・モデル契約
を報告してください。
```
