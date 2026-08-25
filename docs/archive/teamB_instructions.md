# チームB 実装指示書：モデル変更・認証API・出勤不可API

> **担当**: 2人
> **期間**: スプリント2（2週間）
> **更新日**: 2026/7/21

---

## 担当範囲一覧

| # | タスク | ファイル | 工数 |
|---|--------|---------|------|
| B1 | Teacherモデルに `required_periods`, `password_hash` 追加 | `backend/models/teacher.py` | 0.5日 |
| B2 | TeacherUnavailabilityモデル新規作成 | `backend/models/unavailability.py`（新規） | 0.5日 |
| B3 | 教員APIに `required_periods` 対応 | `backend/routes/teachers.py` | 0.5日 |
| B4 | 認証API実装（ログイン・トークン・現在ユーザ） | `backend/routes/auth.py`（新規） | 1日 |
| B5 | 出勤不可CRUD API実装 | `backend/routes/unavailabilities.py`（新規） | 1日 |
| B6 | マイ時間割API実装 | `backend/routes/timetables.py`（改修） | 1日 |
| B7 | シーダー更新（seed教員にrequired_periods, password_hash） | `backend/app.py` | 0.5日 |
| B8 | app.pyに新規Blueprint登録 | `backend/app.py` | 0.5日 |

---

## B1: Teacherモデル変更 (backend/models/teacher.py)

### 変更内容
以下の2カラムを `Teacher` モデルに追加する。

| カラム名 | 型 | デフォルト | 説明 |
|----------|-----|-----------|------|
| `required_periods` | Integer | `5` | 週当たりの必要コマ数 |
| `password_hash` | String(256) | `None` | ログイン用パスワードのハッシュ値 |

### 実装コード

```python
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    employment_type = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    max_online_days = db.Column(db.Integer, default=0, nullable=True)
    # ★ 新規追加フィールド
    required_periods = db.Column(db.Integer, default=5, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)

    def set_password(self, password):
        """プレーンテキストのパスワードをハッシュ化して保存"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """パスワードが正しいか検証"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "employment_type": self.employment_type,
            "department": self.department,
            "subject": self.subject,
            "max_online_days": self.max_online_days,
            "required_periods": self.required_periods,
            # password_hash は to_dict に含めない（セキュリティ）
        }
```

### 依存ライブラリ
`backend/requirements.txt` に以下が含まれていることを確認。なければ追加。

```
Werkzeug>=2.3.0
```

---

## B2: TeacherUnavailabilityモデル新規作成 (backend/models/unavailability.py)

### 設計意図
- 教員ごとに「出勤できない曜日・時限」を管理する
- `period` が `None` の場合は「曜日全体がNG」（全日NG）
- `period` に値がある場合は「特定時限のみNG」
- 同じ教員×曜日×時限の重複登録を禁止（UniqueConstraint）

### 実装コード

```python
from database import db
from sqlalchemy import UniqueConstraint

class TeacherUnavailability(db.Model):
    __tablename__ = 'teacher_unavailabilities'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)  # 'Monday'～'Friday'
    period = db.Column(db.Integer, nullable=True)            # None=全日NG, 1-5=特定時限NG

    teacher = db.relationship('Teacher', backref='unavailabilities')

    __table_args__ = (
        UniqueConstraint('teacher_id', 'day_of_week', 'period', name='u_teacher_unavail'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "day_of_week": self.day_of_week,
            "period": self.period,  # None の場合は全日NG
        }
```

---

## B3: 教員APIに required_periods 対応 (backend/routes/teachers.py)

### 変更内容
既存の教員CRUDに `required_periods` と `password_hash` の設定を追加する。

#### POST（create_teacher）
```python
# create_teacher 関数内の Teacher インスタンス生成箇所
teacher = Teacher(
    name=name,
    employment_type=data.get('employment_type'),
    department=data.get('department'),
    subject=data.get('subject'),
    required_periods=data.get('required_periods', 5),
)
# パスワードが指定されていれば設定
if data.get('password'):
    teacher.set_password(data['password'])
```

#### PUT（update_teacher）
```python
# update_teacher 関数内の更新箇所
teacher.name = name
teacher.employment_type = data.get('employment_type')
teacher.department = data.get('department')
teacher.subject = data.get('subject')
teacher.required_periods = data.get('required_periods', teacher.required_periods)
# パスワードが指定されていれば更新
if data.get('password'):
    teacher.set_password(data['password'])
```

#### GET一覧・個別取得
`to_dict()` に `required_periods` が含まれているので変更不要。

---

## B4: 認証API新規作成 (backend/routes/auth.py)

### 設計
- 簡易トークン認証方式
- ログイン成功時にランダムなトークンを生成し、サーバーのメモリ上の辞書で管理
- 本番環境ではRedisなどに変更可能な構造にしておく

### 実装コード

```python
# backend/routes/auth.py
from flask import Blueprint, jsonify, request
from functools import wraps
import secrets

from database import db
from models.teacher import Teacher

auth_bp = Blueprint('auth_bp', __name__)

# 簡易トークン管理（メモリ上）
# 構造: { token: teacher_id }
_tokens = {}

def generate_token():
    """64文字のランダムトークンを生成"""
    return secrets.token_hex(32)

def login_required(f):
    """認証必須のデコレータ"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "認証が必要です"}), 401
        
        token = auth_header.split(' ', 1)[1]
        teacher_id = _tokens.get(token)
        if teacher_id is None:
            return jsonify({"error": "無効なトークンです"}), 401
        
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return jsonify({"error": "ユーザが見つかりません"}), 401
        
        # リクエストに teacher を付加
        request.current_teacher = teacher
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/login', methods=['POST'])
def login():
    """教員ログイン"""
    data = request.get_json(silent=True) or {}
    
    name = (data.get('name') or '').strip()
    password = data.get('password', '')
    
    if not name or not password:
        return jsonify({"error": "教員名とパスワードは必須です"}), 400
    
    teacher = Teacher.query.filter(
        db.func.lower(Teacher.name) == name.lower()
    ).first()
    
    if not teacher or not teacher.check_password(password):
        return jsonify({"error": "教員名またはパスワードが間違っています"}), 401
    
    # トークン生成（既存トークンがあれば再利用＝同じ端末で再ログインしたときにトークンが増えない）
    existing_token = None
    for t, tid in _tokens.items():
        if tid == teacher.id:
            existing_token = t
            break
    
    if existing_token:
        token = existing_token
    else:
        token = generate_token()
        _tokens[token] = teacher.id
    
    return jsonify({
        "token": token,
        "teacher": teacher.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """現在ログイン中の教員情報を返す"""
    teacher = request.current_teacher
    return jsonify(teacher.to_dict()), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """ログアウト（トークン削除）"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.split(' ', 1)[1]
    
    if token in _tokens:
        del _tokens[token]
    
    return jsonify({"message": "ログアウトしました"}), 200


def get_teacher_id_by_token(token):
    """トークンから教員IDを取得（他モジュールから利用）"""
    return _tokens.get(token)


def get_current_teacher():
    """リクエストから現在の教員を取得（ビュー関数内で使用）"""
    return getattr(request, 'current_teacher', None)
```

---

## B5: 出勤不可CRUD API (backend/routes/unavailabilities.py)

### エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/teachers/<teacher_id>/unavailabilities` | 一覧取得 |
| POST | `/api/teachers/<teacher_id>/unavailabilities` | 一括登録（全置換） |
| DELETE | `/api/teachers/<teacher_id>/unavailabilities/<unavail_id>` | 個別削除 |

### 実装コード

```python
# backend/routes/unavailabilities.py
from flask import Blueprint, jsonify, request
from database import db
from models.teacher import Teacher
from models.unavailability import TeacherUnavailability

unavailabilities_bp = Blueprint('unavailabilities_bp', __name__)

def _get_teacher_or_404(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return None
    return teacher


@unavailabilities_bp.route('/<int:teacher_id>/unavailabilities', methods=['GET'])
def get_unavailabilities(teacher_id):
    """指定教員の出勤不可設定一覧を取得"""
    teacher = _get_teacher_or_404(teacher_id)
    if not teacher:
        return jsonify({"error": "教員が見つかりません"}), 404
    
    unavails = TeacherUnavailability.query.filter_by(teacher_id=teacher_id).all()
    return jsonify({
        "teacher_id": teacher_id,
        "unavailabilities": [u.to_dict() for u in unavails]
    }), 200


@unavailabilities_bp.route('/<int:teacher_id>/unavailabilities', methods=['POST'])
def set_unavailabilities(teacher_id):
    """
    出勤不可設定を一括登録（全置換）。
    既存の設定はすべて削除し、新しい設定で置き換える。
    
    Request body:
    {
        "unavailabilities": [
            {"day_of_week": "Monday", "period": null},   # 月曜全日NG
            {"day_of_week": "Tuesday", "period": 3},      # 火曜3限NG
            ...
        ]
    }
    """
    teacher = _get_teacher_or_404(teacher_id)
    if not teacher:
        return jsonify({"error": "教員が見つかりません"}), 404
    
    data = request.get_json(silent=True) or {}
    new_unavails = data.get('unavailabilities', [])
    
    if not isinstance(new_unavails, list):
        return jsonify({"error": "unavailabilities は配列である必要があります"}), 400
    
    # 既存の設定を全削除
    TeacherUnavailability.query.filter_by(teacher_id=teacher_id).delete()
    
    # 新しい設定を追加
    created = []
    for item in new_unavails:
        day = item.get('day_of_week')
        period = item.get('period')  # None 可
        
        if day not in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            continue
        
        if period is not None and period not in [1, 2, 3, 4, 5]:
            continue
        
        u = TeacherUnavailability(
            teacher_id=teacher_id,
            day_of_week=day,
            period=period
        )
        db.session.add(u)
        created.append(u)
    
    db.session.commit()
    
    return jsonify({
        "message": "出勤不可設定を保存しました",
        "count": len(created),
        "unavailabilities": [u.to_dict() for u in created]
    }), 201


@unavailabilities_bp.route('/<int:teacher_id>/unavailabilities/<int:unavail_id>', methods=['DELETE'])
def delete_unavailability(teacher_id, unavail_id):
    """個別の出勤不可設定を削除"""
    teacher = _get_teacher_or_404(teacher_id)
    if not teacher:
        return jsonify({"error": "教員が見つかりません"}), 404
    
    u = TeacherUnavailability.query.filter_by(id=unavail_id, teacher_id=teacher_id).first()
    if not u:
        return jsonify({"error": "該当する設定が見つかりません"}), 404
    
    db.session.delete(u)
    db.session.commit()
    
    return jsonify({"message": "出勤不可設定を削除しました"}), 200
```

---

## B6: マイ時間割API (backend/routes/timetables.py に追加)

### 既存ファイルへの追加

`backend/routes/timetables.py` の既存インポートに以下を追加：

```python
from routes.auth import login_required  # 認証デコレータ
```

そして、以下のエンドポイントを追加：

```python
@timetables_bp.route('/my', methods=['GET'])
@login_required
def get_my_timetable():
    """ログイン中の教員に割り当てられた時間割を取得"""
    teacher = request.current_teacher
    
    timetables = Timetable.query.filter_by(teacher_id=teacher.id).order_by(
        db.case(
            (Timetable.day_of_week == 'Monday', 1),
            (Timetable.day_of_week == 'Tuesday', 2),
            (Timetable.day_of_week == 'Wednesday', 3),
            (Timetable.day_of_week == 'Thursday', 4),
            (Timetable.day_of_week == 'Friday', 5),
        ),
        Timetable.period
    ).all()
    
    return jsonify({
        "teacher": teacher.to_dict(),
        "timetables": [t.to_dict() for t in timetables]
    }), 200
```

**注意**: インポートに循環参照が発生する可能性があるため、`login_required` のインポートは `timetables.py` の先頭ではなく、関数内で遅延インポートするか、`auth.py` を `timetables.py` より前にインポートするよう `app.py` のBlueprint登録順を調整する。

推奨：`login_required` を共通の `backend/utils/auth_helper.py` に切り出す（循環参照防止のベストプラクティス）。

```python
# backend/utils/auth_helper.py
"""認証関連の共通処理（循環参照防止のために別ファイルに切り出し）"""
from functools import wraps
from flask import jsonify, request
import secrets

_tokens = {}

def generate_token():
    return secrets.token_hex(32)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "認証が必要です"}), 401
        token = auth_header.split(' ', 1)[1]
        teacher_id = _tokens.get(token)
        if teacher_id is None:
            return jsonify({"error": "無効なトークンです"}), 401
        from models.teacher import Teacher
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return jsonify({"error": "ユーザが見つかりません"}), 401
        request.current_teacher = teacher
        return f(*args, **kwargs)
    return decorated

def store_token(token, teacher_id):
    _tokens[token] = teacher_id

def remove_token(token):
    _tokens.pop(token, None)

def get_teacher_id_by_token(token):
    return _tokens.get(token)
```

この場合、`backend/routes/auth.py` も `backend/utils/auth_helper.py` の関数を使用するよう変更する。

---

## B7: シーダー更新 (backend/app.py)

### 変更内容
- seed教員データに `required_periods` と初期パスワードを追加
- seedパスワードは全員 `"password"` で統一（開発用。本番では変更必須）

```python
def _seed_teachers():
    if Teacher.query.count() > 0:
        return
    
    seed_rows = [
        Teacher(name='山田 太郎', employment_type='常勤', department='情報科学科', subject='数学', required_periods=5),
        Teacher(name='田中 花子', employment_type='常勤', department='国語科', subject='国語', required_periods=5),
        Teacher(name='佐藤 次郎', employment_type='常勤', department='英語科', subject='英語', required_periods=5),
        Teacher(name='鈴木 一郎', employment_type='非常勤', department='体育科', subject='体育', required_periods=3),
        Teacher(name='高橋 美咲', employment_type='非常勤', department='美術科', subject='美術', required_periods=2),
    ]
    
    # 全員の初期パスワードを設定
    for t in seed_rows:
        t.set_password('password')
    
    db.session.add_all(seed_rows)
    db.session.commit()
```

---

## B8: app.py に新規Blueprint登録

```python
# app.py の既存インポートに追加
from models.unavailability import TeacherUnAvailability
from routes.unavailabilities import unavailabilities_bp
from routes.auth import auth_bp

# Blueprint登録部に追加
app.register_blueprint(auth_bp, url_prefix='/api/auth')
# 出勤不可APIは teachers のサブリソースとして登録
app.register_blueprint(unavailabilities_bp, url_prefix='/api/teachers')
```

**Blueprint登録順の注意**: `unavailabilities_bp` と `teachers_bp` がどちらも `/api/teachers` をプレフィックスとする。`teachers_bp` の方が先に登録されていることを確認（または優先度の調整が必要な場合は、`teachers_bp` のルートを `/api/teachers` に維持し、`unavailabilities_bp` のルートを相対パスで調整）。

--- 

## db.create_all() について

新しいモデル `TeacherUnavailability` を追加したので、`app.py` の `create_app()` 内で `db.create_all()` が実行されるときに自動的にテーブルが作成される。SQLite開発環境では手動migration不要。

---

## チームAとの連携ポイント

1. **認証APIのIF**：`POST /api/auth/login` の仕様を確定次第、チームAに通知
2. **マイ時間割APIのIF**：`GET /api/timetables/my` のレスポンス形式を確定次第、チームAに通知
3. **出勤不可APIのIF**：`GET/POST/DELETE /api/teachers/<id>/unavailabilities` の仕様を確定次第、チームAに通知
4. **トークン方式**：Bearer トークン方式で統一

## チームCとの連携ポイント

1. **出勤不可データのフォーマット**：チームCが生成ロジックで使用するため、`TeacherUnavailability` モデルの構造を共有
2. **`required_periods`**：チームCが生成ロジックで必要コマ数保証に使用するため、フィールド追加を共有
3. **`auth_helper.py`**：`login_required` デコレータを共通化していることをチームCに伝達

## 完了条件（チームB分）

- [ ] Teacherモデルに `required_periods`, `password_hash` が追加されている
- [ ] TeacherUnavailabilityモデルが作成され、テーブルが自動生成される
- [ ] 教員APIで必要コマ数が登録・更新・取得できる
- [ ] ログインAPIで認証が通る
- [ ] トークンを使って認証が必要なAPIにアクセスできる
- [ ] 出勤不可設定の一括登録・取得・削除ができる
- [ ] マイ時間割APIがログイン中の教員のデータを返す
- [ ] seedデータに必要コマ数とパスワードが設定されている