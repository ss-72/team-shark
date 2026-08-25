# TEAM_B.md
# チームB 実装指示書：自動生成・教員向け機能・結合

> 更新日: 2026-08-25  
> 対象: 学校向け時間割・教室自動割り当てシステム  
> 人数目安: 2人  
> 上位仕様: `docs/PROJECT_PLAN.md`  
> **この文書はGitHub連携・特定のAIエージェントを前提にしない。**
>
> ChatGPT、Gemini、Copilot、その他の生成AIへこの文書をそのまま渡しても、担当範囲と目標を把握できるように記述している。

---

# 1. AIへコードを渡す方法

この文書だけでも、チームBが作るべき機能とアルゴリズム条件は分かる。

実際にコードを書かせる場合は、AIへ最低限次を渡す。

```text
backend/services/timetable_generator.py
backend/models/timetable.py
backend/models/teacher.py
backend/models/classroom.py
backend/models/time_slot.py
backend/routes/timetables.py
backend/app.py
backend/tests/
```

チームA実装後は追加で、

```text
Subject
TeacherSubject
TeacherUnavailability
User / 認証関連
```

のソースも渡す。

教員画面担当には、

```text
frontend/
```

も渡す。

AIがVS Codeやローカルワークスペースを読める場合は、その機能を使用してよい。

GitHubへ直接アクセスできる必要はない。

---

# 2. プロジェクトの現在地

現在すでに存在する主な機能:

- 教員CRUD
- 教室CRUD
- 時間枠CRUD
- 時間割CRUD
- 教員・教室の重複チェック
- 自動生成
- 週間表示

現在の自動生成器は、今回の要求を満たすには不十分。

確認済みの現行挙動:

### 1. 曜日×時限を順番に処理する単純方式

概ね:

```text
Monday 1
Monday 2
...
Friday 5
```

を回し、教員と教室をラウンドロビンで選択する。

### 2. 同一時限に基本1授業しか生成しない

現在の処理は「曜日×時限」ごとに1つの教員・1つの教室を選ぶ構造。

そのため、教室が4室存在しても、

```text
Monday 1限
```

に複数授業を同時配置できない。

今回ここを改善する。

### 3. 以下を考慮していない

- 科目ごとの必要コマ数
- TeacherSubject
- 終日NG
- 特定時限NG
- 科目担当可否

### 4. 生成開始時に既存時間割を削除する

これは今回修正する。

生成不能だった場合に、以前の正常な時間割まで消えるため。

### 5. オンライン均等化

既存機能としてオンライン授業を付ける処理がある。

ただし今回の先生の3要求には含まれていないため、

**新生成器の最優先条件から外す。**

---

# 3. 今回の先生からの要求

## 要求1

```text
この曜日はダメ
この曜日の何時間目はNG
```

を守る。

## 要求2

教員がログインして、

```text
曜日
時限
科目
割当教室
```

を確認できる。

## 要求3

科目ごとの決められたコマ数を、

**自動生成成功時に必ず満たす。**

---

# 4. チームBの役割

チームBは、

**「チームAが登録可能にした条件を使って、正しい時間割を生成し、教員へ結果を見せる」**

チーム。

担当:

1. 自動生成器
2. 制約チェック
3. 生成不能処理
4. 本人時間割API
5. 教員画面
6. 結合・受入テスト

---

# 5. チーム内分担

## B-1: 自動生成エンジン担当

主な対象:

```text
backend/services/timetable_generator.py
backend/routes/timetables.py
backend/tests/
```

### 利用する新モデル

チームAが実装する。

```text
Subject
- id
- name
- required_periods_per_week

TeacherSubject
- teacher_id
- subject_id

TeacherUnavailability
- teacher_id
- day_of_week
- period
```

時間割:

```text
Timetable
- teacher_id
- subject_id
- classroom_id
- day_of_week
- period
```

---

# 6. 自動生成の必須条件

生成成功時、必ずすべて満たす。

### 6.1 科目必要コマ数

各Subjectについて、

```text
生成されたTimetableのsubject_id件数
==
Subject.required_periods_per_week
```

「なるべく満たす」ではなく必須。

---

### 6.2 担当可能教員

TeacherSubjectに登録された教員だけを、その科目の候補とする。

---

### 6.3 終日不可

例:

```text
Teacher A
Tuesday / NULL
```

なら、Aを火曜のどの時限にも配置しない。

---

### 6.4 特定時限不可

例:

```text
Teacher A
Thursday / 3
```

なら、Aを木曜3限に配置しない。

---

### 6.5 教員衝突

同じ、

```text
day_of_week
period
teacher_id
```

を持つ時間割を複数作らない。

---

### 6.6 教室衝突

同じ、

```text
day_of_week
period
classroom_id
```

を複数作らない。

---

### 6.7 並行授業

異なる教員・異なる教室なら、同じ時限に複数授業を生成できる。

正常例:

```text
Monday 1限 / Teacher A / Subject X / Room 101
Monday 1限 / Teacher B / Subject Y / Room 102
```

---

# 7. 生成アルゴリズム方針

高度な最適化は今回の第一目標ではない。

優先順位:

1. 制約を破らない
2. 必要コマ数を満たす
3. 不可能なら正しく失敗する
4. その後で配置の質を改善

推奨処理:

```text
全科目を取得
   ↓
科目ごとの必要コマ数を確認
   ↓
候補教員・候補時間・候補教室を列挙
   ↓
候補が少ない科目から配置
   ↓
必要ならバックトラッキング
   ↓
全制約を最終検証
```

関数を分離することを推奨。

例:

```python
is_teacher_available(...)
teacher_can_teach(...)
is_teacher_free(...)
is_classroom_free(...)
build_candidates(...)
try_assign(...)
validate_schedule(...)
```

既存コードへ巨大なif文を継ぎ足すだけの構造は避ける。

---

# 8. DB保存ルール

ここは重要。

### 禁止

```text
生成開始
↓
Timetable全削除
↓
生成を試す
```

### 正しい方針

```text
DBから条件を読む
       ↓
メモリ上で候補時間割を作る
       ↓
全制約検証
       ↓
成功
  └→ DBの旧時間割と置換してcommit

失敗
  └→ DBを変更しない
```

---

# 9. 生成不能

条件上配置できない場合、

```text
HTTP 422
```

を返す。

最低限、

```text
どの科目が
必要何コマで
何コマしか配置できず
何コマ不足したか
```

を返す。

例:

```json
{
  "error": "timetable_generation_failed",
  "shortages": [
    {
      "subject_id": 1,
      "required": 5,
      "assigned": 3,
      "missing": 2,
      "reason": "available teacher/time slots are insufficient"
    }
  ]
}
```

そして**直前の正常な時間割を残す。**

---

# 10. B-2: 教員本人API・UI・結合担当

## 本人API

目標:

```text
GET /api/my/timetable
```

クライアント側から、

```text
teacher_id=123
```

のように本人IDを自由指定させない。

認証済みUserからteacher_idをサーバー側で特定する。

返却最低項目:

```text
day_of_week
period
subject
classroom
```

---

## 教員画面

最低限:

| 曜日 | 時限 | 科目 | 割当教室 |
|---|---:|---|---|
| Monday | 1 | 科目A | 101 |
| Wednesday | 3 | 科目A | 203 |

これは「空き教室表示」ではない。

**自分の担当授業に割り当てられた教室の表示**。

---

# 11. チームA待ちの間に先行できること

チームAの実装待ちでも、チームBは進められる。

## B-1

- 新アルゴリズム設計
- 候補生成ロジック
- 制約チェック関数
- バックトラッキング
- テストケース設計

実モデル接続だけ後から合わせる。

## B-2

- 教員時間割HTML
- CSS
- 表示JavaScript
- APIレスポンス案
- 401/403時の挙動
- 受入テスト手順

---

# 12. テストケース

最低限以下。

## Test 1: 必要コマ数

```text
Subject X = 3
Subject Y = 2
```

生成後:

```text
X = 3件
Y = 2件
```

---

## Test 2: 終日NG

```text
Teacher A
Tuesday / NULL
```

Aは火曜0件。

---

## Test 3: 時限NG

```text
Teacher A
Thursday / 3
```

Aは木曜3限0件。

---

## Test 4: 担当科目

AがXだけ担当可能なら、YへAを割り当てない。

---

## Test 5: 教員衝突

同一時刻に同じ教員なし。

---

## Test 6: 教室衝突

同一時刻に同じ教室なし。

---

## Test 7: 並行授業

異なる教員・教室なら同時刻に複数授業を配置可能。

---

## Test 8: 生成不能

物理的に必要コマ数を満たせない条件。

期待:

```text
422
不足内容あり
旧時間割が残る
```

---

## Test 9: 本人時間割

Teacher Aでログイン。

Aの時間割のみ返る。

Teacher BのデータをURLやJS操作で取得できない。

---

# 13. チームBが原則変更しないもの

チームA担当:

```text
Userモデルそのもの
認証方式そのもの
Subject CRUD
TeacherSubject管理API
TeacherUnavailability管理API
管理者UI
DB変更基盤
```

必要があっても、モデル/API名称を独自判断で変更しない。

---

# 14. 今回後回し

- オンライン授業均等化
- 教室定員
- 教室間移動最適化
- 連続コマ
- 学年/クラス
- 高度な最適化
- 完璧な時間割スコアリング

今回まず先生の3要求を成立させる。

---

# 15. Definition of Done

- [ ] 科目必要コマ数一致
- [ ] 終日NG厳守
- [ ] 特定時限NG厳守
- [ ] 担当可能科目厳守
- [ ] 教員衝突なし
- [ ] 教室衝突なし
- [ ] 複数教室で並行授業可能
- [ ] 生成不能時422
- [ ] 不足理由あり
- [ ] 生成不能時に旧時間割保持
- [ ] 教員本人の時間割だけ取得可能
- [ ] 割当教室をブラウザ表示可能

---

# 16. 最終受入シナリオ

1. Subject X = 週3コマ
2. Subject Y = 週2コマ
3. Teacher AはX担当
4. Teacher BはY担当
5. Aは火曜終日不可
6. Aは木曜3限不可
7. 自動生成
8. Xが3件、Yが2件
9. AのNG時間に授業なし
10. 教員・教室衝突なし
11. Aでログイン
12. Aの曜日・時限・科目・割当教室だけ表示
13. 配置不能なコマ数へ変更
14. 再生成
15. 422 + 不足理由
16. 直前の正常時間割が残る

---

# 17. 生成AIへそのまま渡せる指示

```text
あなたは学校向け「時間割・教室自動割り当てシステム」の
チームB担当開発者です。

このTEAM_B.mdに書かれた内容を担当範囲の基準にしてください。
PROJECT_PLAN.mdも提供されている場合は、PROJECT_PLAN.mdを最上位仕様として優先してください。

GitHubへ直接アクセスできることは前提にしません。
ソースコードが添付・ワークスペース共有されている場合だけ、そのコードを確認してください。

見えていないコードを想像して、存在しない関数やモデルを断定しないでください。

担当目的は、

1. 科目必要コマ数を必ず満たす
2. 曜日NG・時限NGを守る
3. 担当可能科目を守る
4. 教員・教室衝突を防ぐ
5. 複数授業の並行配置を可能にする
6. 生成不能時は422と不足理由を返す
7. 生成失敗時は旧時間割を残す
8. 教員本人が割当教室を確認できる

ことです。

既存生成器へ無理にif文を積み上げず、
必要なら生成処理を関数単位で再設計してください。

ただし、User/Subject/TeacherSubject/TeacherUnavailability等の
共通モデル名や認証方式を独自に変更しないでください。

ソースが見える場合、作業開始時に、

- 現在の生成器が何をしているか
- 問題点
- 新アルゴリズム案
- 変更予定ファイル
- テストケース

を短く整理してから実装してください。

ソースが見えない場合は、TEAM_B.mdから設計と必要変更点までは作成し、
未確認の実装詳細を推測で断定しないでください。

実装後は、

- 成功ケース
- 生成不能ケース
- 旧時間割保護
- 本人API権限
- 完了項目
- 未完了項目
- 既知の問題

を報告してください。
```
