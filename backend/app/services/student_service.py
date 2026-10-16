from datetime import UTC, datetime
from math import ceil

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.student import Student
from app.repositories.student_repository import StudentRepository
from app.schemas.student import StudentCreate, StudentPage, StudentUpdate


def list_students(
    session: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: str | None,
) -> StudentPage:
    students, total = StudentRepository(session).list(
        page=page,
        page_size=page_size,
        search=search.strip() if search else None,
        status=status,
    )
    return StudentPage(
        items=students,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_student(session: Session, student_id: int) -> Student:
    student = StudentRepository(session).get(student_id)
    if student is None:
        raise APIError(404, "student_not_found", "Student was not found")
    return student


def create_student(session: Session, payload: StudentCreate, created_by: int) -> Student:
    repository = StudentRepository(session)
    email = str(payload.email).lower() if payload.email is not None else None
    _ensure_unique(repository, payload.student_number, email)

    student = Student(
        student_number=payload.student_number,
        full_name=payload.full_name,
        email=email,
        phone=payload.phone,
        status="active",
        created_by=created_by,
    )
    repository.add(student)
    return _commit_student(session, student)


def update_student(
    session: Session,
    student_id: int,
    payload: StudentUpdate,
) -> Student:
    repository = StudentRepository(session)
    student = repository.get(student_id)
    if student is None:
        raise APIError(404, "student_not_found", "Student was not found")

    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).lower()

    _ensure_unique(
        repository,
        changes.get("student_number", student.student_number),
        changes.get("email", student.email),
        exclude_id=student_id,
    )

    requested_status = changes.pop("status", student.status)
    for field_name, value in changes.items():
        setattr(student, field_name, value)
    if requested_status == "archived" and student.status != "archived":
        student.status = "archived"
        student.archived_at = datetime.now(UTC)
    elif requested_status == "active":
        student.status = "active"
        student.archived_at = None
    student.updated_at = datetime.now(UTC)
    return _commit_student(session, student)


def _ensure_unique(
    repository: StudentRepository,
    student_number: str,
    email: str | None,
    *,
    exclude_id: int | None = None,
) -> None:
    if repository.find_by_number(student_number, exclude_id=exclude_id) is not None:
        raise APIError(409, "duplicate_student_number", "A student with this number already exists")
    if email and repository.find_by_email(email, exclude_id=exclude_id) is not None:
        raise APIError(409, "duplicate_student_email", "A student with this email already exists")


def _commit_student(session: Session, student: Student) -> Student:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "student_conflict",
            "Student data conflicts with an existing record",
        ) from None
    session.refresh(student)
    return student