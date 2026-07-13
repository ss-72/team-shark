# 次スプリント計画：BI013・BI015

> **作成日**: 2026/7/10
> **対象**: BI013（非常勤講師優先ルール）、BI015（オンライン授業均等化）

---

## BI013：非常勤講師優先ルール

### 概要
現在の自動生成ロジックは「常勤→非常勤」順で割り当てているが、これを逆にする。
非常勤講師を先に割り当て、空き枠に常勤講師を割り当てる。

### 影響範囲（少量）

| # | ファイル | 変更内容 | 担当 |
|---|---------|---------|------|
| 1 | `backend/services/timetable_generator.py` | 6行目 `desc()` → `asc()` に変更し、非常勤を優先 | **チームB** |
| 2 | `backend/tests/test_api.py` | 非常勤優先のテストケース追加 | **チームB** |

### 改修イメージ

```python
# 現在（6行目）
teachers = Teacher.query.order_by(Teacher.employment_type.desc()).all()

# 変更後
teachers = Teacher.query.order_by(Teacher.employment_type.asc()).all()
# 非常勤('非常勤') < 常勤('常勤') なので非常勤が先に割り当てられる
```

---

## BI015：オンライン授業均等化

### 概要
オンライン授業がある場合、特定の曜日・時限に偏らないように均等に分散する。
新規機能のため、モデル・API・画面すべてに影響あり。

### モデル修正（チームA）

| # | ファイル | 変更内容 | 担当 |
|---|---------|---------|------|
| 1 | `backend/models/teacher.py` | `max_online_days`（週のオンライン上限数, Integer）フィールド追加 | **チームA** |
| 2 | `backend/models/timetable.py` | `is_online`（Boolean, default=False）カラム追加 | **チームA** |
| 3 | `backend/models/classroom.py` | `supports_online`（Boolean, default=False）フィールド追加（任意） | **チームA** |

### ロジック・API・画面修正（チームB）

| # | ファイル | 変更内容 | 担当 |
|---|---------|---------|------|
| 4 | `backend/services/timetable_generator.py` | オンライン授業を均等分散するロジック追加（新規関数 or 既存関数拡張） | **チームB** |
| 5 | `backend/routes/timetables.py` | オンライン授業のAPI対応（POST/PUTでis_onlineを受け付ける） | **チームB** |
| 6 | `frontend/pages/timetables.html` | オンライン授業チェックボックスなどの入力UI追加 | **チームB** |
| 7 | `frontend/js/timetables.js` | オンライン授業データの送信処理追加 | **チームB** |
| 8 | `frontend/js/timetable_view.js` | 週間カレンダーにオンライン授業の表示対応（色分け等） | **チームB** |
| 9 | `backend/tests/test_api.py` | オンライン均等化のテスト追加 | **チームB** |

### 改修イメージ（生成ロジック）

```python
# timetable_generator.py に追加する処理イメージ
def generate_timetable_with_online():
    """オンライン授業を考慮した時間割生成"""
    # 1. オンライン授業を持つ教員を特定
    # 2. 各教員のmax_online_daysを超えないよう制御
    # 3. オンライン授業を異なる曜日に分散配置
    # 4. 教室割り当て時は classroom.supports_online を確認
```

---

## チーム別サマリ

### チームA（マスターデータ管理）

| PBI | タスク | ファイル |
|-----|--------|---------|
| BI015 | Teacherモデルにmax_online_days追加 | `backend/models/teacher.py` |
| BI015 | Timetableモデルにis_online追加 | `backend/models/timetable.py` |
| BI015 | Classroomモデルにsupports_online追加（任意） | `backend/models/classroom.py` |

### チームB（時間割コア機能）

| PBI | タスク | ファイル |
|-----|--------|---------|
| BI013 | ソート順変更（desc→asc） | `backend/services/timetable_generator.py` |
| BI013 | テスト追加 | `backend/tests/test_api.py` |
| BI015 | オンライン均等化ロジック追加 | `backend/services/timetable_generator.py` |
| BI015 | API修正 | `backend/routes/timetables.py` |
| BI015 | 画面UI修正 | `frontend/pages/timetables.html` |
| BI015 | JS修正 | `frontend/js/timetables.js` |
| BI015 | カレンダー表示修正 | `frontend/js/timetable_view.js` |
| BI015 | テスト追加 | `backend/tests/test_api.py` |

---

## 推奨作業順序

```
Week 1
  チームA: Teacher/Timetable/Classroom モデル修正
  チームB: BI013 ソート順変更 + テスト
           ↓
           BI015 オンライン生成ロジック実装
Week 2
  チームB: BI015 API修正 + 画面修正 + テスト