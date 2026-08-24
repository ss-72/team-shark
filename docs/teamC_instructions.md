# チームC 実装指示書：自動生成エンジン改修（制約対応）

> **担当**: 1人
> **期間**: スプリント2（2週間）
> **更新日**: 2026/7/21

---

## 担当範囲一覧

| # | タスク | ファイル | 工数 |
|---|--------|---------|------|
| C1 | 出勤不可制約を生成ロジックに追加 | `backend/services/timetable_generator.py` | 1.5日 |
| C2 | 必要コマ数保証ロジック追加 | `backend/services/timetable_generator.py` | 1.5日 |
| C3 | 既存制約（非常勤優先・重複回避）維持確認 | `backend/services/timetable_generator.py` | 0.5日 |
| C4 | 自動生成APIテスト更新 | `backend/tests/test_api.py` | 1日 |
| C5 | エッジケースのテスト追加 | `backend/tests/test_api.py` | 0.5日 |

---

## 現状のコード理解

現在の `backend/services/timetable_generator.py` は以下の状態：

| 特性 | 現状 |
|------|------|
| 割り当て方式 | 教員と教室を単純にローテーション |
| ソート順 | 非常勤→常勤（正しい） |
| コマ数保証 | **なし**（全教員が均等に割り当てられるだけ） |
| 出勤不可考慮 | **なし** |
| オンライン均等化 | 後処理で実施（_mark_online_evenly） |
| 重複回避 | 使用済みスロットセットで管理 |

### 現状の課題

1. **全教員が均等にしか割り当てられない**
   - 非常勤2コマ、常勤5コマのような差をつけられない
   - `required_periods` を無視している

2. **出勤不可が考慮されていない**
   - 教員が出勤できない曜日・時限にも強制的に割り当てられる

3. **教室の優先学科が考慮されていない（既知、次スプリント）**
   - 今回は対応しない

---

## 改修後の処理フロー

```
generate_timetable()
│
├─ 1. 既存の時間割を全削除
│
├─ 2. 出勤不可マップを事前構築
│      unavail_map[(teacher_id, day, period)] = True
│      （period=None の全日NGは全時限に展開）
│
├─ 3. 教員一覧を取得（非常勤→常勤の順）
│      + required_periods 昇順（少ないコマ数の教員を先に）
│
├─ 4. 教室一覧を取得
│
├─ 5. 必要コマ数アサイン フェーズ
│      for 各教員（非常勤優先）:
│          while 割り当て済みコマ数 < required_periods:
│              空きスロットを探す
│              出勤不可チェック
│              教員重複チェック
│              教室重複チェック
│              割り当て
│
├─ 6. 余剰スロットアサイン フェーズ（オプション）
│      全教員の必要コマ数を満たした後、残りスロットがあれば
│      均等に追加割り当て
│
├─ 7. オンライン均等化（既存の _mark_online_evenly をそのまま使用）
│
└─ 8. Commit & Return
```

---

## C1, C2: timetable_generator.py 完全改修版

```python
# backend/services/timetable_generator.py
from database import db
from models.timetable import Timetable
from models.teacher import Teacher
from models.classroom import Classroom
from models.unavailability import TeacherUnavailability

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = [1, 2, 3, 4, 5]


def generate_timetable():
    """
    時間割を自動生成する。
    制約対応版：出勤不可・必要コマ数保証・非常勤優先・重複回避
    """
    # 1. 既存の時間割をクリア
    Timetable.query.delete()
    db.session.flush()

    # 2. 出勤不可マップを事前構築
    #    キー: (teacher_id, day_of_week, period)
    #    値: True（そのスロットには割り当て不可）
    unavail_map = _build_unavailability_map()

    # 3. 教員一覧を取得
    teachers = Teacher.query.all()
    classrooms = Classroom.query.all()

    if not teachers or not classrooms:
        db.session.commit()
        return []

    # 4. ソート: 非常勤 → 常勤
    #    同じ雇用形態内では required_periods が少ない順
    teachers.sort(key=lambda t: (
        0 if t.employment_type == "非常勤" else 1,
        t.required_periods or 5
    ))

    # 5. 使用済みスロット管理
    used_teacher_slots = set()   # (day, period, teacher_id)
    used_classroom_slots = set() # (day, period, classroom_id)

    # 全スロットのリスト
    all_slots = [(day, period) for day in DAYS for period in PERIODS]

    created = []

    # 6. 必要コマ数アサイン フェーズ
    for teacher in teachers:
        target = teacher.required_periods or 5
        assigned = 0

        # 必要コマ数分、空きスロットを探して割り当て
        for day, period in all_slots:
            if assigned >= target:
                break

            # 出勤不可チェック
            if unavail_map.get((teacher.id, day, period), False):
                continue

            # 教員重複チェック
            teacher_key = (day, period, teacher.id)
            if teacher_key in used_teacher_slots:
                continue

            # 空き教室を探す
            classroom = _find_available_classroom(
                classrooms, day, period, used_classroom_slots
            )
            if classroom is None:
                continue

            # 割り当て実行
            tt = Timetable(
                day_of_week=day,
                period=period,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                is_online=False
            )
            db.session.add(tt)
            created.append(tt)

            used_teacher_slots.add(teacher_key)
            used_classroom_slots.add((day, period, classroom.id))
            assigned += 1

    # 7. 余剰スロットアサイン フェーズ
    #    必要コマ数を満たした教員のうち、まだ余力のある教員に
    #    残りスロットを均等に割り当てる
    for day, period in all_slots:
        for teacher in teachers:
            teacher_key = (day, period, teacher.id)
            if teacher_key in used_teacher_slots:
                continue
            
            # 出勤不可チェック
            if unavail_map.get((teacher.id, day, period), False):
                continue

            # 教室を探す
            classroom = _find_available_classroom(
                classrooms, day, period, used_classroom_slots
            )
            if classroom is None:
                break  # このスロットはもう教室がない

            # 割り当て実行
            tt = Timetable(
                day_of_week=day,
                period=period,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                is_online=False
            )
            db.session.add(tt)
            created.append(tt)

            used_teacher_slots.add(teacher_key)
            used_classroom_slots.add((day, period, classroom.id))
            break  # 1スロットに1教員

    db.session.commit()

    # 8. オンライン均等化（既存ロジック）
    _mark_online_evenly(created)

    return created


def _build_unavailability_map():
    """
    出勤不可マップを構築する。
    
    戻り値:
        dict: { (teacher_id, day, period): True }
    """
    unavail_map = {}
    unavails = TeacherUnavailability.query.all()

    for u in unavails:
        if u.period is None:
            # 全日NG: 全時限をマーク
            for p in PERIODS:
                unavail_map[(u.teacher_id, u.day_of_week, p)] = True
        else:
            # 特定時限NG
            unavail_map[(u.teacher_id, u.day_of_week, u.period)] = True

    return unavail_map


def _find_available_classroom(classrooms, day, period, used_classroom_slots):
    """
    指定したスロットで利用可能な教室を探す。
    
    戻り値:
        Classroom インスタンス or None
    """
    for classroom in classrooms:
        classroom_key = (day, period, classroom.id)
        if classroom_key not in used_classroom_slots:
            return classroom
    return None


def _mark_online_evenly(timetables):
    """
    時間割の中から、できるだけ均等にオンライン授業を割り当てる。
    （既存ロジックをそのまま維持）
    """
    total_slots = len(timetables)
    if total_slots == 0:
        return

    online_count = max(1, total_slots // 5)

    day_groups = {day: [] for day in DAYS}

    for tt in timetables:
        day_groups[tt.day_of_week].append(tt)

    for day, slots in day_groups.items():
        if not slots:
            continue

        step = max(1, len(slots) // max(1, online_count // max(1, len(DAYS))))

        for i in range(0, len(slots), step):
            if online_count <= 0:
                break
            slots[i].is_online = True
            online_count -= 1

    db.session.commit()
```

---

## C3: 既存制約の維持確認チェックリスト

改修後も以下の動作が維持されていることを確認する。

| # | 制約 | 確認方法 | 状態 |
|---|------|---------|------|
| 1 | 教員の重複なし（同じ曜日×時限に同じ教員が複数割り当てられない） | DBのUniqueConstraint + コード上のused_teacher_slots | ✅ 維持 |
| 2 | 教室の重複なし（同じ曜日×時限に同じ教室が複数割り当てられない） | DBのUniqueConstraint + コード上のused_classroom_slots | ✅ 維持 |
| 3 | 非常勤講師が常勤より先に割り当てられる | ソート順 (`0 if 非常勤 else 1`) | ✅ 維持 |
| 4 | オンライン授業が均等に分散される | `_mark_online_evenly` を最後に実行 | ✅ 維持 |
| 5 | 全削除→再生成の挙動 | `Timetable.query.delete()` を先頭で実行 | ✅ 維持 |

---

## C4, C5: テスト更新 (backend/tests/test_api.py)

### 既存テストの確認

まず、既存の `tests/test_api.py` を読み、以下のテストケースが既にあればそのまま維持する。

- `test_generate_timetable` - 自動生成が成功すること
- `test_generate_timetable_duplicates` - 重複がないこと（必要なら追加）

### 追加テストケース

```python
# tests/test_api.py に追加するテスト

def test_generate_respects_unavailability(client, app):
    """出勤不可設定が生成に反映されることを確認"""
    with app.app_context():
        # 教員1（山田太郎）の月曜全日を出勤不可に設定
        from models.unavailability import TeacherUnavailability
        teacher = Teacher.query.filter_by(name='山田 太郎').first()
        
        u = TeacherUnavailability(
            teacher_id=teacher.id,
            day_of_week='Monday',
            period=None  # 全日NG
        )
        db.session.add(u)
        db.session.commit()
    
    # 自動生成を実行
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    
    # 山田太郎が月曜に割り当てられていないことを確認
    for tt in data['timetables']:
        if tt.get('teacher_name') == '山田 太郎':
            assert tt['day_of_week'] != 'Monday', \
                "出勤不可設定（月曜全日NG）が反映されていません"


def test_generate_meets_required_periods(client, app):
    """必要コマ数が満たされることを確認"""
    with app.app_context():
        # seed教員の required_periods を確認
        teacher = Teacher.query.filter_by(name='鈴木 一郎').first()
        # 鈴木一郎は非常勤、required_periods=3 のはず
    
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    
    # 鈴木一郎の割り当て数をカウント
    count = sum(
        1 for tt in data['timetables']
        if tt.get('teacher_name') == '鈴木 一郎'
    )
    
    assert count >= 3, \
        f"鈴木一郎の必要コマ数(3)に対して実際の割り当てが{count}しかありません"


def test_generate_no_duplicate_teacher(client, app):
    """同じ教員が同じ曜日×時限に重複しないことを確認"""
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    
    slots = set()
    for tt in data['timetables']:
        key = (tt['day_of_week'], tt['period'], tt['teacher_id'])
        assert key not in slots, \
            f"教員ID {tt['teacher_id']} が {tt['day_of_week']} {tt['period']}限目に重複しています"
        slots.add(key)


def test_generate_no_duplicate_classroom(client, app):
    """同じ教室が同じ曜日×時限に重複しないことを確認"""
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    
    slots = set()
    for tt in data['timetables']:
        key = (tt['day_of_week'], tt['period'], tt['classroom_id'])
        assert key not in slots, \
            f"教室ID {tt['classroom_id']} が {tt['day_of_week']} {tt['period']}限目に重複しています"
        slots.add(key)


def test_generate_partial_unavailability(client, app):
    """特定時限のみの出勤不可が反映されることを確認"""
    with app.app_context():
        from models.unavailability import TeacherUnavailability
        teacher = Teacher.query.filter_by(name='田中 花子').first()
        
        # 田中花子の火曜3限のみNG
        u = TeacherUnavailability(
            teacher_id=teacher.id,
            day_of_week='Tuesday',
            period=3
        )
        db.session.add(u)
        db.session.commit()
    
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    
    # 田中花子が火曜3限に割り当てられていないことを確認
    for tt in data['timetables']:
        if (tt.get('teacher_name') == '田中 花子' 
            and tt['day_of_week'] == 'Tuesday'
            and tt['period'] == 3):
            assert False, "出勤不可設定（火曜3限NG）が反映されていません"


def test_generate_edge_case_no_teachers(client, app):
    """教員が1人もいない場合でもエラーにならない"""
    with app.app_context():
        # 全教員を一時的に削除（テスト用）
        from models.teacher import Teacher
        Teacher.query.delete()
        db.session.commit()
    
    res = client.post('/api/timetables/generate')
    # 空の結果が返ってくればOK（エラーにはならない）
    assert res.status_code == 201
    data = res.get_json()
    assert data['count'] == 0


def test_generate_edge_case_no_classrooms(client, app):
    """教室が1つもない場合でもエラーにならない"""
    with app.app_context():
        from models.classroom import Classroom
        Classroom.query.delete()
        db.session.commit()
    
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    assert data['count'] == 0


def test_generate_online_evenly_preserved(client, app):
    """オンライン均等化が引き続き機能することを確認"""
    res = client.post('/api/timetables/generate')
    assert res.status_code == 201
    data = res.get_json()
    
    online_slots = [tt for tt in data['timetables'] if tt.get('is_online')]
    assert len(online_slots) > 0, "オンライン授業が1つも割り当てられていません"
    
    # 特定の曜日に偏っていないことを確認（目安: 最大の曜日と最小の曜日の差が2以内）
    day_counts = {}
    for tt in online_slots:
        day = tt['day_of_week']
        day_counts[day] = day_counts.get(day, 0) + 1
    
    counts = list(day_counts.values())
    if len(counts) > 1:
        assert max(counts) - min(counts) <= 2, \
            f"オンライン授業の曜日分散が偏りすぎています: {day_counts}"
```

---

## 注意事項

### 無限ループ対策

必要コマ数が空きスロット数より多い場合、以下の動作とする：

```
if assigned < target:
    # 空きスロット不足で必要コマ数を満たせなかった
    # → 可能な限り割り当てて、残りは諦める
    # （エラーにはしない）
```

これは「全スロットを1周して必要コマ数を満たせなかった」場合に自動的にループが終了する設計になっている。

### DBのUniqueConstraintとの関係

コード上の `used_teacher_slots` / `used_classroom_slots` は二重チェックのための予防的措置。
実際にはDBレベルの `UniqueConstraint` が最終防御となる：

```python
# models/timetable.py に既存
__table_args__ = (
    UniqueConstraint('day_of_week', 'period', 'teacher_id', name='u_teacher_slot'),
    UniqueConstraint('day_of_week', 'period', 'classroom_id', name='u_classroom_slot'),
)
```

### 出勤不可マップの注意

`_build_unavailability_map()` は `TeacherUnavailability` テーブルからデータを読み込む。
このテーブルはチームBが作成するため、チームBの作業完了後に結合テストを行うこと。

### Classroom の優先学科について

今回は対応しない（次スプリントのBI014）。
単純に教室リストから空いている教室を先頭から順に使用する。

---

## チームBとの連携ポイント

1. **`TeacherUnavailability` モデル**：このモデルの構造をチームBから共有してもらう
2. **`required_periods` フィールド**：Teacherモデルに追加されることを前提とする
3. **結合テスト**：チームBのモデル変更完了後、実際に生成ロジックが正しく動作するか確認する

---

## 完了条件（チームC分）

- [ ] 出勤不可設定（全日NG）が自動生成に反映される
- [ ] 出勤不可設定（特定時限NG）が自動生成に反映される
- [ ] 各教員の必要コマ数が満たされる
- [ ] 空きスロット不足時もエラーにならず、可能な限り割り当てられる
- [ ] 既存の教員重複なし・教室重複なしが維持される
- [ ] 既存の非常勤優先ルールが維持される
- [ ] 既存のオンライン均等化が維持される
- [ ] 既存の全削除→再生成の挙動が維持される
- [ ] 上記すべてを確認するテストケースが追加される