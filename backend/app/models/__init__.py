"""LibrePeople HCM models package."""

from .user import User
from .department import Department
from .job import Job
from .employee import Employee, EmployeeHistory
from .custom_field import CustomFieldDef, CustomFieldValue

from .core_hr import LegalEntity, Location, CostCenter, Position, EmployeeDocument, DocumentVersion, DocumentAck, DocumentAccessLog, HRCase, CaseComment

from .recruiting import JobRequisition, Candidate, Application, Offer

from .onboarding import OnboardingTask, OnboardingDocument, TenantPresetState
from .offboarding import Termination, OffboardingTask, OffboardingItem

from .time_attendance import (
    AttendancePeriodLock,
    TimeCorrectionRequest,
    TimeEntry,
    Timesheet,
    WorkingTimeViolation,
)
from .scheduling import ShiftTemplate, RosterEntry, RosterVersion, ShiftSwap

from .leave import LeaveLedgerEntryType, LeaveType, LeaveBalance, LeaveLedger, LeaveRequest

from .payroll import PayrollPeriod, PayComponent, EmployeePayProfile, PayRun, PaySlip

from .performance import Goal, PerformanceReview, ReviewFeedback, CompensationBand, MeritCycle, MeritAllocation

from .benefits import BenefitPlan, BenefitEnrollment, LifeEvent, LeaveOfAbsence

from .expenses import ExpenseCategory, ExpenseClaim, ExpenseReceipt

from .assets import Asset, AssetAssignment

from .learning import Course, CourseEnrollment, Certification, TalentPool, TalentPoolMember, SuccessionPlan

from .compliance import ComplianceRule, ComplianceViolation, HeadcountPlan, Scenario, ReportDefinition, SavedReport

from .audit import AuditLog, AuditChainHead
from .integrity import IntegrityQuarantine
from .integrations_platform import SSOConfig, SCIMToken, Webhook, WebhookDelivery, BackgroundCheck, ESignature

from .refresh_token import RefreshToken
from .job_queue import JobState, JobType, JobQueue

from .client_onboarding import Client, ClientSetting, FeatureFlag, Integration, MigrationJob, OnboardingStep

from .ess_hr import EmployeeSelfService, OrgChartNode, Notification, EmployeeFile, Announcement, EmployeeDirectory, GoalAlignment, ContinuousFeedback, ComplianceCheck

from .forecasting import ForecastRun, ForecastResult, ForecastModelVersion, ForecastScenario, ForecastScenarioResult, CostForecast, CostForecastRow, ForecastAccuracyRecord

from .imports import ImportStatus, ImportDryRun

from app.core.database import Base

__all__ = [
    "User", "Department", "Job", "Employee", "EmployeeHistory",
    "CustomFieldDef", "CustomFieldValue",
    "Location", "CostCenter", "Position", "LegalEntity", "EmployeeDocument", "DocumentVersion", "DocumentAck", "DocumentAccessLog", "HRCase", "CaseComment",
    "JobRequisition", "Candidate", "Application", "Offer",
    "OnboardingTask", "OnboardingDocument", "TenantPresetState", "Termination", "OffboardingTask", "OffboardingItem",
    "TimeEntry", "Timesheet", "WorkingTimeViolation",
    "TimeCorrectionRequest", "AttendancePeriodLock",
    "ShiftTemplate", "RosterEntry", "RosterVersion", "ShiftSwap",
    "LeaveLedgerEntryType", "LeaveType", "LeaveBalance", "LeaveLedger", "LeaveRequest",
    "PayrollPeriod", "PayComponent", "EmployeePayProfile", "PayRun", "PaySlip",
    "Goal", "PerformanceReview", "ReviewFeedback", "CompensationBand", "MeritCycle", "MeritAllocation",
    "BenefitPlan", "BenefitEnrollment", "LifeEvent", "LeaveOfAbsence",
    "ExpenseCategory", "ExpenseClaim", "ExpenseReceipt",
    "Course", "CourseEnrollment", "Certification", "TalentPool", "TalentPoolMember", "SuccessionPlan",
    "ComplianceRule", "ComplianceViolation", "HeadcountPlan", "Scenario", "ReportDefinition", "SavedReport",
    "AuditLog", "AuditChainHead", "IntegrityQuarantine", "SSOConfig", "SCIMToken", "Webhook", "WebhookDelivery", "BackgroundCheck", "ESignature",
    "RefreshToken", "JobState", "JobType", "JobQueue",
    "Client", "ClientSetting", "FeatureFlag", "Integration", "MigrationJob", "OnboardingStep",
    "EmployeeSelfService", "OrgChartNode", "Notification", "EmployeeFile", "Announcement", "EmployeeDirectory", "GoalAlignment", "ContinuousFeedback", "ComplianceCheck",
    "ForecastRun", "ForecastResult", "ForecastModelVersion", "ForecastScenario", "ForecastScenarioResult", "CostForecast", "CostForecastRow", "ForecastAccuracyRecord",
    "ImportStatus", "ImportDryRun",
    "OnboardingTask", "OnboardingDocument", "TenantPresetState", "Termination", "OffboardingTask", "OffboardingItem",
    "PayrollPeriod", "PayComponent", "EmployeePayProfile", "PayRun", "PaySlip",
    "Base",
]
