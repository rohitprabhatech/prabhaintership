from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_assignment import ProjectAssignment


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_project(self, project_id: int, *, lock: bool = False) -> Project | None:
        statement = select(Project).where(Project.project_id == project_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_project_code(self, code: str) -> Project | None:
        return self.session.scalar(
            select(Project).where(func.lower(Project.project_code) == code.lower())
        )

    def list_projects(self, *, page: int, page_size: int, status: str | None):
        statement = select(Project)
        count_statement = select(func.count()).select_from(Project)
        if status is not None:
            statement = statement.where(Project.status == status)
            count_statement = count_statement.where(Project.status == status)
        total = self.session.scalar(count_statement) or 0
        rows = self.session.scalars(
            statement.order_by(func.lower(Project.name), Project.project_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total

    def get_assignment(self, assignment_id: int, *, lock: bool = False) -> ProjectAssignment | None:
        statement = select(ProjectAssignment).where(
            ProjectAssignment.project_assignment_id == assignment_id
        )
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_assignment(self, project_id: int, enrollment_id: int) -> ProjectAssignment | None:
        return self.session.scalar(
            select(ProjectAssignment).where(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.enrollment_id == enrollment_id,
            )
        )

    def list_assignments(
        self,
        *,
        page: int,
        page_size: int,
        enrollment_id: int | None,
        project_id: int | None,
        status: str | None,
    ):
        statement = select(ProjectAssignment, Project)
        count_statement = select(func.count()).select_from(ProjectAssignment)
        statement = statement.join(Project, Project.project_id == ProjectAssignment.project_id)
        filters = []
        if enrollment_id is not None:
            filters.append(ProjectAssignment.enrollment_id == enrollment_id)
        if project_id is not None:
            filters.append(ProjectAssignment.project_id == project_id)
        if status is not None:
            filters.append(ProjectAssignment.status == status)
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        total = self.session.scalar(count_statement) or 0
        rows = self.session.execute(
            statement.order_by(ProjectAssignment.assigned_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return rows, total
