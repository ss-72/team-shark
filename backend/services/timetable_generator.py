from collections import Counter

from database import db
from models.classroom import Classroom
from models.subject import KOMAS_PER_PERIOD, Subject
from models.teacher import Teacher
from models.teacher_subject import TeacherSubject
from models.teacher_unavailability import TeacherUnavailability, VALID_DAYS
from models.timetable import Timetable

DAYS = list(VALID_DAYS)
PERIODS = [1, 2, 3, 4, 5]

DAY_ORDER = {
    'Monday': 0,
    'Tuesday': 1,
    'Wednesday': 2,
    'Thursday': 3,
    'Friday': 4,
}


class TimetableGenerationError(Exception):
    """時間割自動生成が制約を満たせず失敗したことを表す例外"""
    def __init__(self, shortages):
        super().__init__("Timetable generation failed")
        self.shortages = shortages


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


def build_candidates(subject_id, used_teacher_slots=None, used_classroom_slots=None, used_grade_slots=None):
    used_teacher_slots = used_teacher_slots if used_teacher_slots is not None else set()
    used_classroom_slots = used_classroom_slots if used_classroom_slots is not None else set()
    used_grade_slots = used_grade_slots if used_grade_slots is not None else set()
    candidates = []

    subject = db.session.get(Subject, subject_id)
    if not subject:
        return candidates

    eligible_teachers = [
        row.teacher_id for row in TeacherSubject.query.filter_by(subject_id=subject_id).all()
    ]
    for teacher_id in sorted(set(eligible_teachers)):
        if not Teacher.query.get(teacher_id):
            continue
        for day_of_week in DAYS:
            for period in PERIODS:
                if (day_of_week, period, subject.grade) in used_grade_slots:
                    continue
                if not is_teacher_free(teacher_id, day_of_week, period, used_teacher_slots):
                    continue
                for classroom in Classroom.query.order_by(Classroom.id).all():
                    if not is_classroom_free(classroom.id, day_of_week, period, used_classroom_slots):
                        continue
                    candidates.append({
                        'subject_id': subject_id,
                        'grade': subject.grade,
                        'teacher_id': teacher_id,
                        'classroom_id': classroom.id,
                        'day_of_week': day_of_week,
                        'period': period,
                    })
    return sorted(
        candidates,
        key=lambda item: (
            DAY_ORDER.get(item['day_of_week'], 99),
            item['period'],
            item['teacher_id'],
            item['classroom_id'],
            item['subject_id'],
        ),
    )


def try_assign(schedule, candidate, used_teacher_slots=None, used_classroom_slots=None, used_grade_slots=None):
    used_teacher_slots = used_teacher_slots if used_teacher_slots is not None else set()
    used_classroom_slots = used_classroom_slots if used_classroom_slots is not None else set()
    used_grade_slots = used_grade_slots if used_grade_slots is not None else set()
    teacher_key = (candidate['day_of_week'], candidate['period'], candidate['teacher_id'])
    classroom_key = (candidate['day_of_week'], candidate['period'], candidate['classroom_id'])
    grade_key = (candidate['day_of_week'], candidate['period'], candidate['grade'])

    if not teacher_can_teach(candidate['teacher_id'], candidate['subject_id']):
        return False
    if not is_teacher_available(candidate['teacher_id'], candidate['day_of_week'], candidate['period']):
        return False
    if teacher_key in used_teacher_slots or classroom_key in used_classroom_slots or grade_key in used_grade_slots:
        return False

    schedule.append(candidate)
    used_teacher_slots.add(teacher_key)
    used_classroom_slots.add(classroom_key)
    used_grade_slots.add(grade_key)
    return True


def _candidate_shortages(requirements, schedule=None):
    schedule = schedule or []
    counts = Counter()
    classroom_count = Classroom.query.count()
    has_classrooms = classroom_count > 0
    classroom_capacity_is_insufficient = (
        sum(requirements.values())
        > classroom_count * len(DAYS) * len(PERIODS) * KOMAS_PER_PERIOD
    )
    grade_requirements = Counter()
    for subject in Subject.query.all():
        grade_requirements[subject.grade] += requirements.get(subject.id, 0)

    for item in schedule:
        if isinstance(item, Timetable):
            subject_id = item.subject_id
        else:
            subject_id = item['subject_id']

        counts[subject_id] += KOMAS_PER_PERIOD

    shortages = []
    for subject in Subject.query.order_by(Subject.id).all():
        required = requirements.get(subject.id, 0)
        if required <= 0:
            continue
        assigned = counts.get(subject.id, 0)
        if assigned == required:
            continue
        if assigned > required:
            shortages.append({
                'subject_id': subject.id,
                'subject_name': subject.name,
                'required': required,
                'assigned': assigned,
                'missing': required - assigned,
                'reason': 'assigned periods exceed required periods',
            })
            continue

        eligible_teachers = [
            row.teacher_id for row in TeacherSubject.query.filter_by(subject_id=subject.id).all()
        ]
        if not has_classrooms:
            reason = 'no classroom registered'
        elif classroom_capacity_is_insufficient:
            reason = 'classroom capacity is insufficient'
        elif grade_requirements[subject.grade] > len(DAYS) * len(PERIODS) * KOMAS_PER_PERIOD:
            reason = 'grade time slots are insufficient'
        elif not eligible_teachers:
            reason = 'no eligible teacher for subject'
        else:
            reason = 'available teacher/time slots are insufficient'
        shortages.append({
            'subject_id': subject.id,
            'subject_name': subject.name,
            'required': required,
            'assigned': assigned,
            'missing': required - assigned,
            'reason': reason,
        })
    return shortages


def validate_schedule(schedule):
    schedule = list(schedule or [])
    requirements = _subject_requirements()
    teacher_slots = set()
    classroom_slots = set()
    grade_slots = set()
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

        subj = Subject.query.get(subject_id)
        subj_name = subj.name if subj else f"科目ID:{subject_id}"

        if not teacher_can_teach(teacher_id, subject_id):
            return False, [{
                'subject_id': subject_id,
                'subject_name': subj_name,
                'required': requirements.get(subject_id, 0),
                'assigned': counts.get(subject_id, 0),
                'missing': KOMAS_PER_PERIOD,
                'reason': 'teacher is not assigned to the subject',
            }]
        if not is_teacher_available(teacher_id, day_of_week, period):
            return False, [{
                'subject_id': subject_id,
                'subject_name': subj_name,
                'required': requirements.get(subject_id, 0),
                'assigned': counts.get(subject_id, 0),
                'missing': KOMAS_PER_PERIOD,
                'reason': 'teacher is unavailable at that slot',
            }]

        teacher_key = (day_of_week, period, teacher_id)
        classroom_key = (day_of_week, period, classroom_id)
        grade_key = (day_of_week, period, subj.grade if subj else None)
        if teacher_key in teacher_slots or classroom_key in classroom_slots or grade_key in grade_slots:
            return False, [{
                'subject_id': subject_id,
                'subject_name': subj_name,
                'required': requirements.get(subject_id, 0),
                'assigned': counts.get(subject_id, 0),
                'missing': KOMAS_PER_PERIOD,
                'reason': 'teacher or classroom conflict detected',
            }]

        teacher_slots.add(teacher_key)
        classroom_slots.add(classroom_key)
        grade_slots.add(grade_key)
        counts[subject_id] += KOMAS_PER_PERIOD

    shortages = _candidate_shortages(requirements, schedule)
    if shortages:
        return False, shortages
    return True, []


def generate_candidate_schedule():
    requirements = _subject_requirements()

    if not requirements:
        return []

    classroom_capacity = (
        Classroom.query.count() * len(DAYS) * len(PERIODS) * KOMAS_PER_PERIOD
    )
    if sum(requirements.values()) > classroom_capacity:
        raise TimetableGenerationError(_candidate_shortages(requirements))

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

    # 1時限は2コマなので、必要コマ数を時限数へ変換してタスクを作る
    task_queue = []

    for item in subject_candidates:
        subject = item['subject']

        task_queue.extend(
            [subject.id] * (subject.required_periods_per_week // KOMAS_PER_PERIOD)
        )

    chosen = []
    used_teacher_slots = set()
    used_classroom_slots = set()
    used_grade_slots = set()

    def backtrack(index):
        if index == len(task_queue):
            is_valid, shortages = validate_schedule(chosen)
            return is_valid, shortages

        subject_id = task_queue[index]

        options = build_candidates(
            subject_id,
            used_teacher_slots,
            used_classroom_slots,
            used_grade_slots,
        )

        day_load = Counter(item['day_of_week'] for item in chosen)
        options.sort(key=lambda item: (
            day_load[item['day_of_week']],
            DAY_ORDER.get(item['day_of_week'], 99),
            item['period'],
            item['teacher_id'],
            item['classroom_id'],
            item['subject_id'],
        ))

        for option in options:
            candidate = {
                'subject_id': option['subject_id'],
                'grade': option['grade'],
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
            grade_key = (
                candidate['day_of_week'],
                candidate['period'],
                candidate['grade'],
            )

            if teacher_key in used_teacher_slots:
                continue

            if classroom_key in used_classroom_slots or grade_key in used_grade_slots:
                continue

            chosen.append(candidate)
            used_teacher_slots.add(teacher_key)
            used_classroom_slots.add(classroom_key)
            used_grade_slots.add(grade_key)

            success, shortages = backtrack(index + 1)

            if success:
                return True, []

            used_teacher_slots.remove(teacher_key)
            used_classroom_slots.remove(classroom_key)
            used_grade_slots.remove(grade_key)
            chosen.pop()

        return False, _candidate_shortages(
            requirements,
            chosen
        )

    success, shortages = backtrack(0)

    if not success:
        actual_shortages = (
            shortages
            or _candidate_shortages(
                requirements,
                chosen
            )
        )
        raise TimetableGenerationError(actual_shortages)

    return chosen


def generate_timetable():
    """時間割を自動生成し、成功時のみ既存データを置換する。"""
    candidate_schedule = generate_candidate_schedule()

    try:
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
    except Exception:
        db.session.rollback()
        raise
