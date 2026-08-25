# チームA 実装指示書：ユーザ管理・ログイン・マイ時間割表示

> **担当**: 2人
> **期間**: スプリント2（2週間）
> **更新日**: 2026/7/21

---

## 担当範囲一覧

| # | タスク | ファイル | 工数 |
|---|--------|---------|------|
| A1 | ログインページ作成 | `frontend/pages/login.html`（新規） | 0.5日 |
| A2 | ログイン処理JS実装 | `frontend/js/login.js`（新規） | 0.5日 |
| A3 | 認証フロントエンド結合 | 上記2ファイル | 0.5日 |
| A4 | マイ時間割ページ作成 | `frontend/pages/my_timetable.html`（新規） | 1日 |
| A5 | マイ時間割JS実装 | `frontend/js/my_timetable.js`（新規） | 1日 |
| A6 | 教員管理画面に必要コマ数追加 | `frontend/pages/teachers.html`, `frontend/js/teachers.js` | 0.5日 |
| A7 | 出勤不可設定画面作成 | `frontend/pages/my_availability.html`（新規） | 1日 |
| A8 | 出勤不可設定JS実装 | `frontend/js/my_availability.js`（新規） | 0.5日 |

---

## A1: ログインページ (login.html)

### 要件
- 教員が自身のID（または名前）とパスワードでログインできるシンプルなフォーム
- ログイン成功時はトークンを `localStorage` に保存し、`my_timetable.html` にリダイレクト
- ログイン失敗時はエラーメッセージを画面に表示

### 画面イメージ

```
┌──────────────────────────┐
│        【ログイン】       │
│                          │
│  教員名: [____________]  │
│  パスワード: [________]  │
│                          │
│  [ログイン]              │
│                          │
│  × 教員名またはパスワード │
│    が間違っています       │
└──────────────────────────┘
```

### API仕様（チームBと連携）

```
POST /api/auth/login
Request:  { "name": "山田 太郎", "password": "xxx" }
Response: { "token": "abc123...", "teacher": { "id": 1, "name": "山田 太郎", ... } }
```

### 実装のポイント
1. `form` タグで `submit` イベントをハンドリング
2. `fetch` で `POST /api/auth/login` を呼び出し
3. 成功時: `localStorage.setItem('token', response.token)` + `localStorage.setItem('teacher_id', response.teacher.id)`
4. 失敗時: 赤色のエラーメッセージをフォーム下部に表示
5. すでにログイン済み（トークンがある）場合は `my_timetable.html` にリダイレクト

---

## A2: ログイン処理JS (login.js)

### 実装内容

```javascript
// login.js

const API_BASE = 'http://localhost:5000/api';

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('name').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('errorMessage');
    
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
    
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, password })
        });
        
        if (!res.ok) {
            const data = await res.json();
            errorDiv.textContent = data.error || 'ログインに失敗しました';
            errorDiv.style.display = 'block';
            return;
        }
        
        const data = await res.json();
        localStorage.setItem('token', data.token);
        localStorage.setItem('teacher_id', data.teacher.id);
        localStorage.setItem('teacher_name', data.teacher.name);
        
        window.location.href = 'my_timetable.html';
        
    } catch (err) {
        errorDiv.textContent = 'サーバーに接続できません';
        errorDiv.style.display = 'block';
    }
});

// ログイン済みチェック
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = 'my_timetable.html';
    }
});
```

---

## A4, A5: マイ時間割ページ (my_timetable.html / my_timetable.js)

### 要件
- ログイン中の教員に割り当てられた教室を「曜日×時限」の表で表示
- 表の各セルには「教室名」を表示（例: "101教室"）
- 割り当てがないセルは「-」を表示
- 対面授業とオンライン授業は色分け（対面: 白背景、オンライン: 薄青背景）
- 画面上部に「ログアウト」ボタン
- 未ログインの場合はログインページにリダイレクト

### 画面イメージ

```
┌──────────────────────────────────────────────────┐
│  ようこそ、山田 太郎 さん    [ログアウト]         │
│                                                    │
│  自分に割り当てられた教室                          │
│                                                    │
│  ┌────────┬──────┬──────┬──────┬──────┬──────┐   │
│  │        │ 月   │ 火   │ 水   │ 木   │ 金   │   │
│  ├────────┼──────┼──────┼──────┼──────┼──────┤   │
│  │ 1限目  │101教室│  -   │201教室│  -   │理科室│   │
│  ├────────┼──────┼──────┼──────┼──────┼──────┤   │
│  │ 2限目  │  -   │体育館│  -   │101教室│  -   │   │
│  ├────────┼──────┼──────┼──────┼──────┼──────┤   │
│  │ 3限目  │  -   │  -   │101教室│  -   │201教室│   │
│  ├────────┼──────┼──────┼──────┼──────┼──────┤   │
│  │ 4限目  │201教室│  -   │  -   │体育館│  -   │   │
│  ├────────┼──────┼──────┼──────┼──────┼──────┤   │
│  │ 5限目  │  -   │  -   │  -   │  -   │  -   │   │
│  └────────┴──────┴──────┴──────┴──────┴──────┘   │
│                                                    │
│  [出勤不可設定を変更する] ← リンク                  │
└──────────────────────────────────────────────────┘
```

### API仕様（チームBと連携）

```
GET /api/timetables/my
Headers: { Authorization: 'Bearer <token>' }
Response: {
    "timetables": [
        {
            "id": 1,
            "day_of_week": "Monday",
            "period": 1,
            "classroom_name": "101教室",
            "is_online": false
        },
        ...
    ]
}
```

### my_timetable.js 実装イメージ

```javascript
const API_BASE = 'http://localhost:5000/api';
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const DAYS_JP = ['月', '火', '水', '木', '金'];
const PERIODS = [1, 2, 3, 4, 5];

// 認証チェック
const token = localStorage.getItem('token');
if (!token) {
    window.location.href = 'login.html';
}

// 教員名表示
document.getElementById('teacherName').textContent = localStorage.getItem('teacher_name');

// 時間割データ取得
async function loadMyTimetable() {
    const res = await fetch(`${API_BASE}/timetables/my`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    
    // データをマップに変換: map[day][period] = classroom_name
    const tableData = {};
    data.timetables.forEach(t => {
        if (!tableData[t.day_of_week]) tableData[t.day_of_week] = {};
        tableData[t.day_of_week][t.period] = t;
    });
    
    // テーブルを描画
    renderTable(tableData);
}

function renderTable(data) {
    const tbody = document.getElementById('timetableBody');
    tbody.innerHTML = '';
    
    PERIODS.forEach(period => {
        const tr = document.createElement('tr');
        const periodCell = document.createElement('td');
        periodCell.textContent = `${period}限目`;
        tr.appendChild(periodCell);
        
        DAYS.forEach(day => {
            const td = document.createElement('td');
            const entry = data[day]?.[period];
            if (entry) {
                td.textContent = entry.classroom_name || '教室なし';
                if (entry.is_online) {
                    td.classList.add('online-class');
                }
            } else {
                td.textContent = '-';
                td.classList.add('empty-slot');
            }
            tr.appendChild(td);
        });
        
        tbody.appendChild(tr);
    });
}

// ログアウト
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.clear();
    window.location.href = 'login.html';
});

loadMyTimetable();
```

---

## A6: 教員管理画面に必要コマ数追加 (teachers.html / teachers.js)

### 変更内容

#### teachers.html
- 教員登録・編集フォームに `required_periods` フィールドを追加
- 数値入力（1〜25、デフォルト5）

```html
<div class="form-group">
    <label for="required_periods">必要コマ数（週）</label>
    <input type="number" id="required_periods" name="required_periods" 
           min="1" max="25" value="5" required>
</div>
```

#### teachers.js
- 登録・更新時に `required_periods` を送信
- 一覧表示に `required_periods` を追加

---

## A7, A8: 出勤不可設定画面 (my_availability.html / my_availability.js)

### 要件
- ログイン中の教員が自分の出勤不可日時を設定できる
- チェックボックス形式で「曜日全体」と「時限単位」を設定
- 現在の設定を表示（読み込み時に反映）
- 設定は「保存」ボタンで確定
- 画面上部に「マイ時間割に戻る」リンク

### 画面イメージ

```
┌────────────────────────────────────────────┐
│  出勤不可設定 - 山田 太郎                   │
│  [← マイ時間割に戻る]                      │
│                                              │
│  ┌─────┬────┬────┬────┬────┬────┬────┐    │
│  │     │ 月 │ 火 │ 水 │ 木 │ 金 │    │    │
│  ├─────┼────┼────┼────┼────┼────┼────┤    │
│  │全日  │ □  │ □  │ □  │ □  │ □  │    │    │
│  ├─────┼────┼────┼────┼────┼────┼────┤    │
│  │1限目 │ □  │ □  │ □  │ □  │ □  │    │    │
│  ├─────┼────┼────┼────┼────┼────┼────┤    │
│  │2限目 │ □  │ □  │ □  │ □  │ □  │    │    │
│  ├─────┼────┼────┼────┼────┼────┼────┤    │
│  │3限目 │ □  │ □  │ □  │ □  │ □  │    │    │
│  ├─────┼────┼────┼────┼────┼────┼────┤    │
│  │4限目 │ □  │ □  │ □  │ □  │ □  │    │    │
│  ├─────┼────┼────┼────┼────┼────┼────┤    │
│  │5限目 │ □  │ □  │ □  │ □  │ □  │    │    │
│  └─────┴────┴────┴────┴────┴────┴────┘    │
│                                              │
│  [保存]                                      │
│                                              │
│  ✅ 保存しました                             │
└──────────────────────────────────────────────┘
```

### 実装のポイント
1. 「全日」チェックボックスがONの場合、その曜日の全時限が自動的にONになる（JSで制御）
2. 「全日」をOFFにしても、個別にONにした時限はそのまま残る
3. 保存時は現在の全チェック状態をAPIに送信（差分ではなく全置換）

---

## スタイルについて

- 既存の `frontend/css/style.css` に以下を追納して使用
- 新規CSSクラスは最小限に

```css
/* マイ時間割用 */
.online-class {
    background-color: #e3f2fd;
}
.empty-slot {
    color: #ccc;
}
```

---

## チームBとの連携ポイント

1. **認証APIの仕様**：`POST /api/auth/login` のリクエスト/レスポンス形式をチームBと事前に合意
2. **マイ時間割API**：`GET /api/timetables/my` のレスポンス形式をチームBと事前に合意
3. **出勤不可API**：`GET/POST/DELETE /api/teachers/<id>/unavailabilities` の仕様をチームBと事前に合意
4. **トークン方式**：Bearer トークン方式、トークンの有効期限は一旦設けない

## 完了条件（チームA分）

- [ ] ログインページが表示され、認証が通る
- [ ] ログイン成功後、マイ時間割ページに遷移する
- [ ] マイ時間割ページに自分に割り当てられた教室が表形式で表示される
- [ ] オンライン授業と対面授業が色分け表示される
- [ ] ログアウトが機能する
- [ ] 出勤不可設定画面でチェックのON/OFFができ、保存できる
- [ ] 教員管理画面で必要コマ数が設定できる