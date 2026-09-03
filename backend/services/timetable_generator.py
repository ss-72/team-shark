from collections import Counter

from database import db
from models.classroom import Classroom
from models.subject import Subject
from models.teacher import Teacher
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability, VALID_DAYS
from models.timetable import Timetable

DAYS = list(VALID_DAYS)
PERIODS = [1, 2, 3, 4, 5]


def teacher_can_teach(teacher_id, subject_id):
    return bool(
        TeacherSubject.query.filter_by(teacher_id=teacher_id, subject_id=subject_id).first()
    )


def is_teacher_available(teacher_id, day_of_week, period):
    if TeacherUnavailability.query.filter_by(
        teacher_id=teacher_id,
        day_of_week=day_of_week,
        period=None,
    ).first():
        return False
    if TeacherUnavailability.query.filter_by(
        teacher_id=teacher_id,
        day_of_week=day_of_week,
        period=period,
    ).first():
        return False
    return True


def is_teacher_free(teacher_id, day_of_week, period, used_teacher_slots=None):
    used_teacher_slots = used_teacher_slots or set()
    if not is_teacher_available(teacher_id, day_of_week, period):
        return False
    return (day_of_week, period, teacher_id) not in used_teacher_slots


def is_classroom_free(classroom_id, day_of_week, period, used_classroom_slots=None):
    used_classroom_slots = used_classroom_slots or set()
    return (day_of_week, period, classroom_id) not in used_classroom_slots


def _subject_requirements():
    return {
        subject.id: subject.required_periods_per_week
        for subject in Subject.query.all()
        if subject.required_periods_per_week and subject.required_periods_per_week > 0
    }


def build_candidates(subject_id, used_teacher_slots=None, used_classroom_slots=None):
    used_teacher_slots = used_teacher_slots or set()
    used_classroom_slots = used_classroom_slots or set()
    candidates = []

    eligible_teachers = [
        row.teacher_id for row in TeacherSubject.query.filter_by(subject_id=subject_id).all()
    ]
    for teacher_id in sorted(set(eligible_teachers)):
        if not Teacher.query.get(teacher_id):
            continue
        for day_of_week in DAYS:
            for period in PERIODS:
                if not is_teacher_free(teacher_id, day_of_week, period, used_teacher_slots):
                    continue
                for classroom in Classroom.query.order_by(Classroom.id).all():
                    if not is_classroom_free(classroom.id, day_of_week, period, used_classroom_slots):
                        continue
                    candidates.append({
                        'subject_id': subject_id,
                        'teacher_id': teacher_id,
                        'classroom_id': classroom.id,
                        'day_of_week': day_of_week,
                        'period': period,
                    })
    return sorted(
        candidates,
        key=lambda item: (
            item['day_of_week'],
            item['period'],
            item['teacher_id'],
            item['classroom_id'],
            item['subject_id'],
        ),
    )


def try_assign(schedule, candidate, used_teacher_slots=None, used_classroom_slots=None):
    used_teacher_slots = used_teacher_slots or set()
    used_classroom_slots = used_classroom_slots or set()
    teacher_key = (candidate['day_of_week'], candidate['period'], candidate['teacher_id'])
    classroom_key = (candidate['day_of_week'], candidate['period'], candidate['classroom_id'])

    if not teacher_can_teach(candidate['teacher_id'], candidate['subject_id']):
        return False
    if not is_teacher_available(candidate['teacher_id'], candidate['day_of_week'], candidate['period']):
        return False
    if teacher_key in used_teacher_slots or classroom_key in used_classroom_slots:
        return False

    schedule.append(candidate)
    used_teacher_slots.add(teacher_key)
    used_classroom_slots.add(classroom_key)
    return True


def _candidate_shortages(requirements, schedule=None):
    schedule = schedule or []
    counts = Counter()

    for item in schedule:
        if isinstance(item, Timetable):
            subject_id = item.subject_id
        else:
            subject_id = item['subject_id']

        counts[subject_id] += 1

    shortages = []
    for subject in Subject.query.order_by(Subject.id).all():
        required = requirements.get(subject.id, 0)
        if required <= 0:
            continue
        assigned = counts.get(subject.id, 0)
        if assigned >= required:
            continue
        eligible_teachers = [
            row.teacher_id for row in TeacherSubject.query.filter_by(subject_id=subject.id).all()
        ]
        if not eligible_teachers:
            reason = 'no eligible teacher for subject'
        else:
            reason = 'available teacher/time slots are insufficient'
        shortages.append({
            'subject_id': subject.id,
            'required': required,
            'assigned': assigned,
            'missing': required - assigned,
            'reason': reason,
        })
    return shortages


def validate_schedule(schedule):
    schedule = list(schedule or [])
    teacher_slots = set()
    classroom_slots = set()
    counts = Counter()

    for item in schedule:
        if isinstance(item, Timetable):
            subject_id = item.subject_id
            teacher_id = item.teacher_id
            classroom_id = item.classroom_id
            day_of_week = item.day_of_week
            period = item.period
        else:
            subject_id = item['subject_id']
            teacher_id = item['teacher_id']
            classroom_id = item['classroom_id']
            day_of_week = item['day_of_week']
            period = item['period']

        if not teacher_can_teach(teacher_id, subject_id):
            return False, [{
                'subject_id': subject_id,
                'required': 0,
                'assigned': counts.get(subject_id, 0),
                'missing': 1,
                'reason': 'teacher is not assigned to the subject',
            }]
        if not is_teacher_available(teacher_id, day_of_week, period):
            return False, [{
                'subject_id': subject_id,
                'required': 0,
                'assigned': counts.get(subject_id, 0),
                'missing': 1,
                'reason': 'teacher is unavailable at that slot',
            }]

        teacher_key = (day_of_week, period, teacher_id)
        classroom_key = (day_of_week, period, classroom_id)
        if teacher_key in teacher_slots or classroom_key in classroom_slots:
            return False, [{
                'subject_id': subject_id,
                'required': 0,
                'assigned': counts.get(subject_id, 0),
                'missing': 1,
                'reason': 'teacher or classroom conflict detected',
            }]

        teacher_slots.add(teacher_key)
        classroom_slots.add(classroom_key)
        counts[subject_id] += 1

    requirements = _subject_requirements()
    shortages = _candidate_shortages(requirements, schedule)
    if shortages:
        return False, shortages
    return True, []


def generate_candidate_schedule():
    requirements = _subject_requirements()

    if not requirements:
        return []

    subjects = Subject.query.filter(
        Subject.required_periods_per_week > 0
    ).all()

    # 候補数の少ない科目を先にする
    subject_candidates = []

    for subject in subjects:
        candidates = build_candidates(subject.id)

        subject_candidates.append({
            'subject': subject,
            'candidate_count': len(candidates)
        })

    subject_candidates.sort(
        key=lambda item: (
            item['candidate_count'],
            item['subject'].required_periods_per_week,
            item['subject'].id
        )
    )

    # 必要コマ数分だけタスクを作る
    task_queue = []

    for item in subject_candidates:
        subject = item['subject']

        task_queue.extend(
            [subject.id] * subject.required_periods_per_week
        )

    chosen = []
    used_teacher_slots = set()
    used_classroom_slots = set()

    def backtrack(index):
        if index == len(task_queue):
            is_valid, shortages = validate_schedule(chosen)
            return is_valid, shortages

        subject_id = task_queue[index]

        options = build_candidates(
            subject_id,
            used_teacher_slots,
            used_classroom_slots
        )

        for option in options:
            candidate = {
                'subject_id': option['subject_id'],
                'teacher_id': option['teacher_id'],
                'classroom_id': option['classroom_id'],
                'day_of_week': option['day_of_week'],
                'period': option['period'],
            }

            teacher_key = (
                candidate['day_of_week'],
                candidate['period'],
                candidate['teacher_id']
            )

            classroom_key = (
                candidate['day_of_week'],
                candidate['period'],
                candidate['classroom_id']
            )

            if teacher_key in used_teacher_slots:
                continue

            if classroom_key in used_classroom_slots:
                continue

            chosen.append(candidate)
            used_teacher_slots.add(teacher_key)
            used_classroom_slots.add(classroom_key)

            success, shortages = backtrack(index + 1)

            if success:
                return True, []

            used_teacher_slots.remove(teacher_key)
            used_classroom_slots.remove(classroom_key)
            chosen.pop()

        return False, _candidate_shortages(
            requirements,
            chosen
        )

    success, shortages = backtrack(0)

    if not success:
        raise ValueError({
            'error': 'timetable_generation_failed',
            'shortages': (
                shortages
                or _candidate_shortages(
                    requirements,
                    chosen
                )
            )
        })

    return chosen


def generate_timetable():
    """時間割を自動生成し、成功時のみ既存データを置換する。"""
    candidate_schedule = generate_candidate_schedule()

    Timetable.query.delete()
    created = []
    for item in candidate_schedule:
        timetable = Timetable(
            day_of_week=item['day_of_week'],
            period=item['period'],
            teacher_id=item['teacher_id'],
            subject_id=item['subject_id'],
            classroom_id=item['classroom_id'],
            is_online=False,
        )
        db.session.add(timetable)
        created.append(timetable)

    db.session.commit()
    return created