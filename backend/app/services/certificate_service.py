from datetime import UTC, datetime
from math import ceil

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate
from app.models.certificate_event import CertificateEvent
from app.models.enrollment import Enrollment
from app.repositories.certificate_repository import CertificateRepository
from app.schemas.finance import (
    CertificateEventCreate,
    CertificateEventResponse,
    CertificateIssueCreate,
    CertificateReplacementCreate,
    CertificateReportPage,
    CertificateResponse,
)
from app.services.business_number_service import generate_business_number


def list_certificates(
    session: Session,
    *,
    page: int,
    page_size: int,
    status: str | None,
    enrollment_id: int | None,
    search: str | None,
) -> CertificateReportPage:
    rows, total = CertificateRepository(session).list_report(
        page=page,
        page_size=page_size,
        status=status,
        enrollment_id=enrollment_id,
        search=search.strip() if search else None,
    )
    return CertificateReportPage(
        items=[CertificateResponse.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_certificate(session: Session, certificate_id: int) -> CertificateResponse:
    row = CertificateRepository(session).status_row(certificate_id)
    if row is None:
        raise APIError(404, "certificate_not_found", "Certificate was not found")
    return CertificateResponse.model_validate(row)


def issue_certificate(
    session: Session,
    payload: CertificateIssueCreate,
    admin_id: int,
    request_id,
) -> CertificateResponse:
    enrollment = session.scalar(
        select(Enrollment)
        .where(Enrollment.enrollment_id == payload.enrollment_id)
        .with_for_update()
    )
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    issued_at = payload.issued_at or datetime.now(UTC)
    if issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise APIError(422, "timezone_required", "Certificate issue time must include a timezone")
    certificate = Certificate(
        enrollment_id=enrollment.enrollment_id,
        certificate_number=generate_business_number(session, "certificate"),
        certificate_type=payload.certificate_type,
        issued_at=issued_at,
        document_uri=payload.document_uri,
        issued_by=admin_id,
    )
    session.add(certificate)
    try:
        session.flush()
        _audit(session, admin_id, "certificate_issued", certificate, request_id, {})
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(409, "certificate_conflict", "Certificate number already exists") from None
    return get_certificate(session, certificate.certificate_id)


def replace_certificate(
    session: Session,
    certificate_id: int,
    payload: CertificateReplacementCreate,
    admin_id: int,
    request_id,
) -> CertificateResponse:
    repository = CertificateRepository(session)
    original = repository.get(certificate_id)
    if original is None:
        raise APIError(404, "certificate_not_found", "Certificate was not found")
    enrollment = session.scalar(
        select(Enrollment)
        .where(Enrollment.enrollment_id == original.enrollment_id)
        .with_for_update()
    )
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    current = repository.status_row(certificate_id)
    if current is None or current["derived_status"] != "issued":
        raise APIError(
            409, "certificate_not_replaceable", "Only an issued certificate can be replaced"
        )
    issued_at = payload.issued_at or datetime.now(UTC)
    if issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise APIError(422, "timezone_required", "Certificate issue time must include a timezone")

    replacement = Certificate(
        enrollment_id=original.enrollment_id,
        certificate_number=generate_business_number(session, "certificate"),
        certificate_type=original.certificate_type,
        issued_at=issued_at,
        document_uri=payload.document_uri,
        replaces_certificate_id=original.certificate_id,
        issued_by=admin_id,
    )
    session.add(replacement)
    try:
        session.flush()
        event = CertificateEvent(
            certificate_id=original.certificate_id,
            event_type="replaced",
            related_certificate_id=replacement.certificate_id,
            reason=payload.reason,
            recorded_by=admin_id,
        )
        session.add(event)
        _audit(
            session,
            admin_id,
            "certificate_replaced",
            original,
            request_id,
            {"replacement_id": replacement.certificate_id, "reason": payload.reason},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "certificate_conflict", "Certificate replacement conflicts with existing history"
        ) from None
    return get_certificate(session, replacement.certificate_id)


def revoke_certificate(
    session: Session,
    certificate_id: int,
    payload: CertificateEventCreate,
    admin_id: int,
    request_id,
) -> CertificateEventResponse:
    return _append_certificate_event(
        session,
        certificate_id,
        "revoked",
        payload.reason,
        admin_id,
        request_id,
    )


def record_certificate_correction(
    session: Session,
    certificate_id: int,
    payload: CertificateEventCreate,
    admin_id: int,
    request_id,
) -> CertificateEventResponse:
    return _append_certificate_event(
        session,
        certificate_id,
        "corrected",
        payload.reason,
        admin_id,
        request_id,
    )


def _append_certificate_event(
    session: Session,
    certificate_id: int,
    event_type: str,
    reason: str,
    admin_id: int,
    request_id,
) -> CertificateEventResponse:
    repository = CertificateRepository(session)
    certificate = repository.get(certificate_id)
    if certificate is None:
        raise APIError(404, "certificate_not_found", "Certificate was not found")
    enrollment = session.scalar(
        select(Enrollment)
        .where(Enrollment.enrollment_id == certificate.enrollment_id)
        .with_for_update()
    )
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    current = repository.status_row(certificate_id)
    if current is None or current["derived_status"] != "issued":
        raise APIError(
            409, "certificate_not_active", "Only an issued certificate can receive this event"
        )
    event = CertificateEvent(
        certificate_id=certificate_id,
        event_type=event_type,
        reason=reason,
        recorded_by=admin_id,
    )
    session.add(event)
    try:
        session.flush()
        _audit(
            session,
            admin_id,
            f"certificate_{event_type}",
            certificate,
            request_id,
            {"reason": reason},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "certificate_event_conflict", "Certificate already has a terminal event"
        ) from None
    session.refresh(event)
    return CertificateEventResponse.model_validate(event)


def list_certificate_events(
    session: Session, certificate_id: int
) -> list[CertificateEventResponse]:
    repository = CertificateRepository(session)
    if repository.get(certificate_id) is None:
        raise APIError(404, "certificate_not_found", "Certificate was not found")
    return [
        CertificateEventResponse.model_validate(event)
        for event in repository.events(certificate_id)
    ]


def _audit(
    session: Session,
    admin_id: int,
    action: str,
    certificate: Certificate,
    request_id,
    metadata: dict,
) -> None:
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action=action,
            target_type="certificate",
            target_id=certificate.certificate_id,
            request_id=request_id,
            metadata_=metadata,
        )
    )
