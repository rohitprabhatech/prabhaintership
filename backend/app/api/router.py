from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.batches import router as batches_router
from app.api.routes.certificates import router as certificates_router
from app.api.routes.enrollment_finance import (
    payment_adjustment_router,
)
from app.api.routes.enrollment_finance import (
    router as enrollment_finance_router,
)
from app.api.routes.enrollments import router as enrollments_router
from app.api.routes.health import router as health_router
from app.api.routes.programs import router as programs_router
from app.api.routes.projects import router as projects_router
from app.api.routes.students import router as students_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["admin-authentication"])
api_router.include_router(students_router)
api_router.include_router(programs_router)
api_router.include_router(batches_router)
api_router.include_router(enrollments_router)
api_router.include_router(enrollment_finance_router)
api_router.include_router(payment_adjustment_router)
api_router.include_router(projects_router)
api_router.include_router(certificates_router)
