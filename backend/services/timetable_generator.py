from database import db
from models.timetable import Timetable
from models.teacher import Teacher
from models.classroom import Classroom

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
PERIODS = [1, 2, 3, 4, 5]

def generate_timetable():
    """時間割を自動生成する。既存データは全削除して再生成する。"""

    # 1. 既存の時間割をクリア
    Timetable.query.delete()

    # 2. 教員一覧を取得（非常勤→常勤の順）
    teachers = Teacher.query.all()
    teachers.sort(
        key=lambda t: 0 if t.employment_type == "非常勤" else 1
    )

    # 3. 教室一覧を取得
    classrooms = Classroom.query.all()

    # 4. 使用済みスロットを管理
    used_slots = set()

    created = []

    # 5. 教員ごとに空いている枠を探して割り当て
    for teacher in teachers:
        assigned = False

        for day in DAYS:
            if assigned:
                break

            for period in PERIODS:
                if assigned:
                    break

                for classroom in classrooms:
                    teacher_key = (day, period, teacher.id)
                    classroom_key = (day, period, classroom.id)

                    if teacher_key not in used_slots and classroom_key not in used_slots:
                        tt = Timetable(
                            day_of_week=day,
                            period=period,
                            teacher_id=teacher.id,
                            classroom_id=classroom.id
                        )

                        db.session.add(tt)
                        created.append(tt)

                        used_slots.add(teacher_key)
                        used_slots.add(classroom_key)

                        assigned = True
                        break

    db.session.commit()

    _mark_online_evenly(created)

    return created


def _mark_online_evenly(timetables):
    """
    時間割の中から、できるだけ均等にオンライン授業を割り当てる。
    """

    total_slots = len(timetables)
    online_count = max(1, total_slots // 5)

    day_groups = {day: [] for day in DAYS}

    for tt in timetables:
        day_groups[tt.day_of_week].append(tt)

    for day, slots in day_groups.items():
        if not slots:
            continue

        step = max(1, len(slots) // online_count)

        for i in range(0, len(slots), step):
            if online_count <= 0:
                break

            slots[i].is_online = True
            online_count -= 1

    db.session.commit()