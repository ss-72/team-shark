# チームB 実装指示書
## 自動生成・教員向け機能・結合チーム

> 更新日: 2026-08-25  
> 上位仕様: `docs/PROJECT_PLAN.md`  
> この文書はチームBの担当範囲・実装順序・完了条件を定義する。仕様が衝突した場合は必ず `PROJECT_PLAN.md` を優先する。

---

## 0. 生成AIに渡すときの前提

生成AIには最低限、次を読ませる。

- `docs/PROJECT_PLAN.md`
- `docs/TEAM_B.md`
- `backend/services/timetable_generator.py`
- 関連するmodels/routes
- 教員向け既存フロントコード

`docs/archive/` は旧仕様であり、現行仕様の根拠にはしない。

Git運用方法はこの文書では扱わない。

---

# 1. チームBの目的

チームBは、**登録された条件から正しい時間割を生成し、教員本人が自分に割り当てられた教室を確認できる状態を完成させる**。

担当領域:

1. 自動生成エンジン
2. 生成成功・失敗の検証
3. 本人用時間割API
4. 教員向け画面
5. 結合・受入テスト

5人を2チームに分ける場合、チームBは2人を想定する。

---

# 2. B-1 自動生成エンジン担当

## 主担当

```text
backend/services/timetable_generator.py
POST /api/timetables/generate 周辺
生成器テスト
```

現行の単純ラウンドロビン方式は今回の要求を満たせないため、必要に応じて生成処理を再設計する。

## 必須制約

生成成功時はすべて満たす。

1. 科目ごとの必要コマ数
2. 担当可能教員のみ割当
3. 教員の終日不可
4. 教員の特定時限不可
5. 教員の同時刻重複禁止
6. 教室の同時刻重複禁止
7. 複数教室を使った同一時限の並行授業
8. 制約を満たせない場合は失敗
9. 失敗時は既存時間割を保持

## 入力データ

チームAが提供する。

```text
Subject
- id
- required_periods_per_week

TeacherSubject
- teacher_id
- subject_id

TeacherUnavailability
- teacher_id
- day_of_week
- period

Teacher
Classroom
TimeSlot
```

## 出力

各時間割行:

```text
teacher_id
subject_id
classroom_id
day_of_week
period
```

## 最重要ルール

生成開始時に既存TimetableをDELETEしない。

正しい流れ:

```text
1. DBから条件取得
2. メモリ上で候補時間割を生成
3. 全制約を検証
4. 成功時のみDBを置換
5. 失敗時は既存DBを変更しない
```

## 生成不能

HTTP 422。

最低限、次のように不足が理解できる情報を返す。

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

## アルゴリズム方針

最適化よりまず制約厳守。

推奨:

```text
候補の少ない科目から配置
  ↓
担当可能教員を列挙
  ↓
不可日時を除外
  ↓
教員・教室が空いている候補枠を列挙
  ↓
配置
  ↓
全件検証
```

必要ならバックトラッキングを使う。

既存ラウンドロビンへ大量のifを継ぎ足すだけの実装は避ける。

## 今回後回し

- オンライン授業均等化
- 教室移動距離
- 教室定員最適化
- 連続コマ
- 学年・クラス
- 高度なスコア最適化

---

# 3. B-2 教員UI・本人API・結合担当

## 本人時間割API

```text
GET /api/my/timetable
```

重要:

クライアントから任意の `teacher_id` を指定させない。

ログインユーザーに紐付くteacherをサーバー側で判定し、その教員の時間割だけ返す。

最低限の返却情報:

```text
day_of_week
period
subject
classroom
```

## 教員向け画面

最低限:

| 曜日 | 時限 | 科目 | 割当教室 |
|---|---:|---|---|
| Monday | 1 | 科目A | 101 |
| Wednesday | 3 | 科目A | 203 |

この画面の目的は空き教室検索ではない。

**本人の授業に割り当て済みの教室を表示すること**。

## 権限テスト

- 未ログイン → 401
- teacher A → A本人のみ
- URL/JSを変更してもteacher Bの時間割を取得できない

## 結合担当

チームAのAPI・認証と生成器を接続し、先生の3要求が一連の操作として成立することを確認する。

---

# 4. チームBの実装順序

## Step 1
現行生成器を読む。

```text
backend/services/timetable_generator.py
backend/models/timetable.py
関連models/routes
```

## Step 2
テストケースを先に定義。

### 正常
- Subject X = 3コマ
- Subject Y = 2コマ
- 生成後 X=3、Y=2

### 終日不可
- Teacher A / Tuesday / NULL
- 火曜にAが入らない

### 特定時限不可
- Teacher A / Thursday / 3
- 木曜3限にAが入らない

### 担当科目
- AがXのみ担当可能ならYには配置しない

### 教員衝突
同一曜日・時限に同じ教員を2件置かない。

### 教室衝突
同一曜日・時限に同じ教室を2件置かない。

### 並行授業
異なる教員・教室なら同一時限に複数授業を置ける。

### 生成不能
- 422
- 不足理由
- 旧時間割保持

## Step 3
生成器実装。

## Step 4
`/api/my/timetable`。

## Step 5
教員UI。

## Step 6
PROJECT_PLANの受入テスト。

---

# 5. チームA待ちの間にできること

## B-1

先行可能:

- 生成アルゴリズム設計
- 制約チェック関数
- 候補生成関数
- バックトラッキング
- テストケース

例:

```text
is_teacher_available(...)
can_assign(...)
build_candidates(...)
validate_candidate_timetable(...)
```

## B-2

先行可能:

- 教員時間割画面HTML/CSS
- 表示JS
- `/api/my/timetable` の期待JSON設計
- 401/403時の画面挙動
- 受入手順作成

---

# 6. チームBが原則触らない領域

チームA主担当:

```text
Userモデル本体
認証方式そのもの
Subject CRUD
TeacherSubject管理API
TeacherUnavailability管理API
管理者向け設定UI
DB変更の基盤
```

モデル名・API名をチームB独自で変更しない。

---

# 7. 生成器の重要ルール

## 必要コマ数

成功時:

```text
Timetableでのsubject_id件数
==
Subject.required_periods_per_week
```

「なるべく満たす」ではなく必須。

## 担当可能教員

TeacherSubjectに存在する教員だけ候補。

## 不可時間

以下どちらかに該当したら割当不可:

```text
teacher_id + day + NULL
teacher_id + day + period
```

## 教員衝突

```text
day_of_week + period + teacher_id
```

重複禁止。

## 教室衝突

```text
day_of_week + period + classroom_id
```

重複禁止。

## 並行授業

以下は正常:

```text
Monday 1限 / Teacher A / Room 101
Monday 1限 / Teacher B / Room 102
```

---

# 8. 保存前バリデーション

候補時間割をDBへ保存する前に:

```text
全Subjectの必要コマ数 == 割当数
全行でTeacherSubject成立
全行でTeacherUnavailability非該当
教員衝突なし
教室衝突なし
```

1つでもNGなら保存しない。

---

# 9. 今日の優先順位

## 最優先

- [ ] 新生成器の設計
- [ ] テストケース作成
- [ ] 不可条件チェック
- [ ] 担当科目チェック
- [ ] 教員/教室衝突チェック
- [ ] 科目必要コマ数チェック

## 次

- [ ] バックトラッキング/再試行
- [ ] 失敗時に旧時間割保持
- [ ] 422レポート

## 余裕があれば

- [ ] `/api/my/timetable`
- [ ] 教員時間割画面
- [ ] ログイン後導線

---

# 10. Definition of Done

- [ ] 必要コマ数一致
- [ ] 曜日NGを破らない
- [ ] 時限NGを破らない
- [ ] 未担当科目を割り当てない
- [ ] 教員重複なし
- [ ] 教室重複なし
- [ ] 同一時限に複数教室を使える
- [ ] 生成不能時422
- [ ] 生成不能時に旧時間割保持
- [ ] 教員本人の時間割だけ取得可能
- [ ] 割当教室をブラウザで確認可能
- [ ] PROJECT_PLANの受入テストを通せる

---

# 11. 生成AI向け作業開始指示

```text
あなたは「時間割・教室自動割り当てシステム」のチームB担当開発者です。

最上位仕様は docs/PROJECT_PLAN.md、
担当範囲は docs/TEAM_B.md です。

最初に両文書と、
backend/services/timetable_generator.py、
関連するTimetable/Teacher/Classroomモデルとrouteを確認してください。

docs/archive/ は旧仕様です。
古いモデル名・API名を現行仕様より優先しないでください。

チームBの目的は、
1. 科目必要コマ数を満たす
2. 教員の曜日/時限NGを守る
3. 担当可能科目を守る
4. 教員・教室衝突を防ぐ
5. 生成不能時は既存時間割を保護して理由を返す
6. 教員本人が割当教室を確認できる
状態を完成させることです。

既存生成器へ無理にif文を積み上げず、必要なら生成処理を関数単位で再設計してください。

User/Subject等のモデル名や認証方式は独自変更しないでください。
それらはチームAとの共通契約です。

作業前に、
- 現行生成器の問題点
- 新アルゴリズム案
- 変更ファイル
- テストケース
を短く整理してください。

実装後は、
- 成功ケース
- 生成不能ケース
- 旧時間割保護
- 本人時間割の権限
をテストし、完了・未完了・既知問題を報告してください。
```

---

# 12. 最終受入シナリオ

1. Subject X = 週3コマ
2. Subject Y = 週2コマ
3. Teacher AはX担当
4. Teacher BはY担当
5. Aは火曜終日不可
6. Aは木曜3限不可
7. 自動生成
8. X=3、Y=2
9. AのNG日時に割当なし
10. 教員・教室重複なし
11. Aでログイン
12. Aの曜日・時限・科目・割当教室のみ表示
13. 配置不能な必要コマ数へ変更
14. 再生成
15. 422 + 不足理由
16. 直前の正常時間割が保持される
