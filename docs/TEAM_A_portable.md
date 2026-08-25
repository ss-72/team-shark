# TEAM_A.md
# チームA 実装指示書：基盤・認証・管理機能

> 更新日: 2026-08-25  
> 対象: 学校向け時間割・教室自動割り当てシステム  
> 人数目安: 3人  
> 上位仕様: `docs/PROJECT_PLAN.md`  
> **この文書はGitHub連携・特定のAIエージェントを前提にしない。**
>
> ChatGPT、Gemini、Copilot、その他の生成AIへこの文書をそのまま渡しても、担当範囲と目標を把握できるように記述している。

---

## 1. この文書だけをAIに渡す場合

この文書だけでも「何を作るべきか」は判断できる。

ただし、実際にコードを変更させる場合は、AIに以下のどれかを与えること。

### 方法A: AIがVS Code / ワークスペースを読める場合
この文書を渡し、記載されたファイルを確認させる。

### 方法B: 普通のChatGPT / Gemini等を使う場合
必要なソースファイルを添付・貼り付けする。

最低限、作業内容に応じて次を渡す。

```text
backend/app.py
backend/models/
backend/routes/
backend/tests/
```

フロントを担当する場合:

```text
frontend/
```

### ソースが渡されていない場合のAIのルール

見えていないコードを勝手に想像して完成コードを断定しないこと。

その場合は、

1. この文書から目標仕様を整理
2. 必要な変更ファイルを列挙
3. 実装案を作成
4. 実コード確認後に確定すべき部分を明示

まで行う。

---

# 2. プロジェクトの現在地

このシステムは Flask + SQLAlchemy + HTML/CSS/JavaScript で作られている。

現在すでに存在する主な機能:

- 教員CRUD
- 教室CRUD
- 時間枠CRUD
- 時間割CRUD
- 教員・教室の同時刻重複チェック
- 自動生成エンドポイント
- 週間カレンダー表示
- オンライン授業関連の既存処理

現在確認できている主なバックエンド構成:

```text
backend/
├─ app.py
├─ models/
│  ├─ classroom.py
│  ├─ teacher.py
│  ├─ time_slot.py
│  └─ timetable.py
├─ routes/
│  ├─ classrooms.py
│  ├─ teachers.py
│  ├─ time_slots.py
│  └─ timetables.py
├─ services/
│  └─ timetable_generator.py
└─ tests/
   └─ test_api.py
```

現時点では、以下はまだ本格実装されていない。

```text
User
Subject
TeacherSubject
TeacherUnavailability
Timetable.subject_id
認証API
本人時間割API
```

既存 `Teacher` は概ね以下の情報を持っている。

```text
id
name
employment_type
department
subject
max_online_days
```

既存の `Teacher.subject` は文字列であり、今後の正式な科目管理には使用しない。

既存 `Timetable` は概ね以下。

```text
id
day_of_week
period
is_online
teacher_id
classroom_id
```

同一曜日・時限で、

- teacher重複
- classroom重複

を禁止する既存制約がある。

---

# 3. 今回の先生からの最優先要求

今回の改修は次の3点を成立させるために行う。

### 要求1
教員ごとに、

- この曜日は出勤不可
- この曜日のこの時限は出勤不可

を設定できること。

### 要求2
教員がログインし、

- 曜日
- 時限
- 科目
- 自分に割り当てられた教室

を確認できること。

### 要求3
自動生成した時間割が、

**科目ごとに決められた週当たり必要コマ数を必ず満たすこと。**

---

# 4. チームAの役割

チームAは、

**「先生の要求を表現できるデータ構造と管理機能を作り、チームBへ安定した入力データを提供する」**

チームである。

担当:

1. データモデル
2. DB変更
3. 認証・権限
4. 管理API
5. 管理者向けUI
6. テスト基盤整理

自動生成アルゴリズム本体と教員本人画面はチームB担当。

---

# 5. チーム内分担

## A-1: 基盤・認証担当

主担当:

```text
Userモデル
認証
権限
DB初期化/変更
app.pyへの登録
テスト用seed整理
```

### 新規Userモデル

目標:

```text
User
- id
- username
- password_hash
- role
- teacher_id
- is_active
```

必須ルール:

- usernameは一意
- パスワード平文保存禁止
- roleは `admin` / `teacher`
- teacherユーザーはTeacherと紐付く
- 無効ユーザーはログイン不可

### 認証API

目標:

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
```

基本方針:

**HTTP-onlyセッションCookie**

管理APIはadminのみ利用可能。

### HTTPステータス

```text
未認証      -> 401
権限不足    -> 403
入力不正    -> 400系
```

### A-1完了条件

- 管理者ログイン
- 教員ログイン
- logout
- auth/me
- パスワードhash化
- teacherが管理APIへアクセスすると拒否

---

## A-2: 科目・制約モデル/API担当

担当:

```text
Subject
TeacherSubject
TeacherUnavailability
Timetable.subject_id
関連管理API
```

### Subject

```text
Subject
- id
- name
- required_periods_per_week
```

ルール:

- name一意
- `required_periods_per_week >= 1`

重要:

必要コマ数は**教員単位ではなく科目単位**。

`Teacher.required_periods` は作らない。

---

### TeacherSubject

```text
TeacherSubject
- teacher_id
- subject_id
```

意味:

「この教員はこの科目を担当可能」

同じ組み合わせの重複は禁止。

---

### TeacherUnavailability

```text
TeacherUnavailability
- id
- teacher_id
- day_of_week
- period
```

例:

```text
Tuesday / NULL
→ 火曜は終日不可

Thursday / 3
→ 木曜3限のみ不可
```

曜日:

```text
Monday
Tuesday
Wednesday
Thursday
Friday
```

`period = NULL` は終日不可。

同じ条件の重複は禁止。

---

### Timetable変更

既存Timetableへ、

```text
subject_id
```

を追加する。

今後の正式な時間割1件:

```text
teacher_id
subject_id
classroom_id
day_of_week
period
```

---

### 管理API

最低限:

```text
/api/subjects
/api/teachers/<id>/subjects
/api/teachers/<id>/unavailable-slots
```

CRUDまたは必要十分なGET/POST/PUT/DELETEを実装。

### A-2完了条件

- 科目登録
- 必要コマ数登録
- 教員担当科目登録
- 終日NG登録
- 特定時限NG登録
- Timetableにsubject保存
- 不正ID・不正値を4xxで拒否

---

## A-3: 管理画面・テスト担当

管理者がブラウザから必要データを入力できるようにする。

最低限必要な管理機能:

1. 科目管理
2. 必要コマ数設定
3. 教員の担当科目設定
4. 教員の出勤不可設定
5. 必要であればUser管理

デザインの豪華さより、

**誰が操作しても設定できること**

を優先。

既存のHTML/CSS/JavaScriptを再利用してよい。

---

# 6. DB変更時の重要注意

現在のアプリは `db.create_all()` を利用している。

`db.create_all()` は新規テーブルを作ることはできるが、

**既存Timetableテーブルへsubject_id列を安全に追加するマイグレーションにはならない。**

開発環境で既存データが不要なら、

- DBを作り直す

でもよい。

データ保持が必要なら、

- Flask-Migrate / Alembic等

を検討。

採用した方法はチーム内で共有する。

---

# 7. 現在のテストについて

既存 `backend/tests/test_api.py` には、現在のseed処理と一致しない古い期待値が残っている可能性が高い。

例として確認済みの問題:

- アプリが教員をseedする一方、テストが「追加後1件」を期待
- 教室も同様
- TimeSlotのseed件数とテスト期待値が一致していない
- 自動生成テストも現在の生成器・seedと前提が合っていない

新機能追加前に、

```bash
python -m unittest discover -s backend/tests
```

が安定するように整理する。

推奨:

**TESTING時は自動seedを無効にし、テスト自身が必要データを作る。**

---

# 8. チームBへ渡す共通契約

チームBは以下を利用する。

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

チームAは、これらの名前を独自に変更しない。

変更が必要な場合は両チームで共有する。

---

# 9. チームAが原則変更しない部分

```text
backend/services/timetable_generator.py
GET /api/my/timetable
教員本人向け時間割画面
自動生成アルゴリズム
生成失敗理由
```

これらはチームB担当。

---

# 10. 作業優先順位

## Priority 1

- [ ] 既存テスト・seed整理
- [ ] User
- [ ] Subject
- [ ] TeacherSubject
- [ ] TeacherUnavailability
- [ ] Timetable.subject_id

## Priority 2

- [ ] 認証API
- [ ] 科目API
- [ ] 担当科目API
- [ ] 不可条件API

## Priority 3

- [ ] 管理UI
- [ ] User管理
- [ ] 手動時間割登録時の新制約検証

---

# 11. Definition of Done

チームA完了条件:

- [ ] 新モデルがDBで利用可能
- [ ] 科目ごとの必要コマ数を保存可能
- [ ] 教員と科目を紐付け可能
- [ ] 教員の曜日/時限NGを保存可能
- [ ] Timetableにsubject_idが存在
- [ ] 管理APIが動作
- [ ] ログイン・権限制御が動作
- [ ] 管理画面から必要情報を入力可能
- [ ] チームBがモデル仕様を推測せず利用可能
- [ ] テストが通る
- [ ] 既存CRUDを致命的に破壊していない

---

# 12. 生成AIへそのまま渡せる指示

以下はChatGPT、Gemini、Copilot等にそのまま貼り付けて使用可能。

```text
あなたは学校向け「時間割・教室自動割り当てシステム」の
チームA担当開発者です。

このTEAM_A.mdに書かれた仕様を担当範囲の基準にしてください。
PROJECT_PLAN.mdも提供されている場合は、PROJECT_PLAN.mdを最上位仕様として優先してください。

GitHubへ直接アクセスできることは前提にしません。
ソースコードが添付・ワークスペース共有されている場合だけ、そのコードを確認してください。

見えていないコードを想像して存在しない関数・ファイルを断定しないでください。

担当目的は次の通りです。

1. User・認証・権限
2. Subject
3. TeacherSubject
4. TeacherUnavailability
5. Timetable.subject_id
6. 管理API
7. 管理者向けUI
8. テスト基盤

自動生成アルゴリズム本体と教員本人向け画面はチームB担当なので、
timetable_generator.pyを勝手に全面変更しないでください。

ソースが見える場合は最初に現状を確認し、
この文書に書かれた「現在地」と差分があれば実コードの現状を報告してください。

作業開始時に以下を短く示してください。

- 現在実装済みのもの
- 今回担当するタスク
- 変更予定ファイル
- 実装順序

その後実装してください。

実装後は必ず、

- 完了した項目
- テスト結果
- 未完了項目
- 既知の問題
- チームBへ共有すべきモデル/API

をまとめてください。
```
