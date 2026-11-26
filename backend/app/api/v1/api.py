from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    employees,
    departments,
    jobs,
    requisitions,
    candidates,
    applications,
    offers,
    interviews,
    onboarding,
    time_attendance,
    scheduling,
    leave,
    offboarding,
    reports,
    filings,
    client_onboarding,
    core_hr,
    payroll,
    performance,
    benefits,
    learning,
    integrations_platform,
    compliance,
    import_export,
    data_quality,
    ess_hr,
    expenses,
    assets,
    forecasting,
    admin_jobs,
    admin_audit,
    admin_status,
    break_glass,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(
    requisitions.router, prefix="/requisitions", tags=["requisitions"]
)
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(
    applications.router, prefix="/applications", tags=["applications"]
)
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(time_attendance.router, prefix="/time", tags=["time"])
api_router.include_router(scheduling.router, prefix="/scheduling", tags=["scheduling"])
api_router.include_router(leave.router, prefix="/leave", tags=["leave"])
api_router.include_router(
    offboarding.router, prefix="/offboarding", tags=["offboarding"]
)
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(filings.router, prefix="/reports", tags=["reports"])
api_router.include_router(
    client_onboarding.router, prefix="/onboarding-portal", tags=["client-onboarding"]
)
api_router.include_router(core_hr.router, prefix="/core-hr", tags=["core-hr"])
# The public door. It is mounted on its own so that it is visibly separate
# from the case queue it feeds.
api_router.include_router(core_hr.public_router, prefix="/public", tags=["public"])
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])
api_router.include_router(benefits.router, prefix="/benefits", tags=["benefits"])
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])
api_router.include_router(
    integrations_platform.router, prefix="/platform", tags=["platform"]
)
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
api_router.include_router(import_export.router, prefix="/import-export", tags=["import-export"])
api_router.include_router(data_quality.router, prefix="/data-quality", tags=["data-quality"])
api_router.include_router(ess_hr.router, prefix="/ess", tags=["ess-hr"])
api_router.include_router(
    forecasting.router, prefix="/forecasting", tags=["forecasting"]
)
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(admin_jobs.router, prefix="/admin/jobs", tags=["admin"])
api_router.include_router(admin_audit.router, prefix="/admin/audit", tags=["admin"])
api_router.include_router(admin_status.router, prefix="/admin/status", tags=["admin"])
api_router.include_router(
    break_glass.router, prefix="/break-glass", tags=["break-glass"]
)
