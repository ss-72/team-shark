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
    
    # 2. 教員一覧を取得（常勤→非常勤の順でソート）
    teachers = Teacher.query.order_by(Teacher.employment_type.desc()).all()
    
    # 3. 教室一覧を取得
    classrooms = Classroom.query.all()
    
    # 4. 使用済みスロットを管理するセット
    used_slots = set()  # (day_of_week, period, teacher_id) と (day_of_week, period, classroom_id)
    
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
                    
                # 空いている教室を探す
                for classroom in classrooms:
                    teacher_key = (day, period, teacher.id)
                    classroom_key = (day, period, classroom.id)
                    
                    if teacher_key not in used_slots and classroom_key not in used_slots:
                        # 割り当て
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
    return created
