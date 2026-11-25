from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class OnboardingTaskBase(BaseModel):
    employee_id: int
    title: str
    description: Optional[str] = None
    category: str = "General"
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "Pending"


class OnboardingTaskCreate(OnboardingTaskBase):
    pass


class OnboardingTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None


class OnboardingTaskOut(OnboardingTaskBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OnboardingDocumentOut(BaseModel):
    id: int
    employee_id: int
    document_type: str
    file_name: str
    storage_url: str
    status: str
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OnboardingDocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    status: Optional[str] = None


class OnboardingSummary(BaseModel):
    """Aggregated onboarding status for one employee."""

    employee_id: int
    total_tasks: int
    completed_tasks: int
    progress_percent: int
    documents_uploaded: int


# --------------------------------------------------------------------------
# Presets, the difference report and the readiness check
# --------------------------------------------------------------------------
#
# A preset is a document, not a decision. These schemas describe what the
# server reports about one: what it proposes, what it would change, and
# what is still missing. Nothing here is a mutation.


class PresetSummaryOut(BaseModel):
    """One preset in the catalogue.

    The shape is the contract's ``OnboardingPreset``: the identifier, the
    name, the industry, the module keys, the default roles and the
    recommended settings.
    """

    id: str
    name: str
    industry: Optional[str] = None
    modules: list[str] = []
    default_roles: list[dict] = []
    recommended_settings: dict = {}
    version: str
    status: str
    description: str


class PresetDetailOut(PresetSummaryOut):
    """One preset in full."""

    business_type: str
    created_at: str
    updated_at: str
    module_dependencies: dict[str, list[str]] = {}
    organisation_templates: dict = {}
    dashboards: dict = {}
    forecast_drivers: dict = {}
    import_templates: list[dict] = []
    validations: list[dict] = []
    exclusions: list[dict] = []
    configuration: dict = {}
    preset: dict = {}


class SettingChangeOut(BaseModel):
    """One setting, and what the preset would do with it."""

    path: str
    module: str
    action: str
    preset_value: Optional[object] = None
    tenant_value: Optional[object] = None
    note: str = ""


class ProvenanceOut(BaseModel):
    """Where one configured value came from."""

    path: str
    module: str
    state: str
    origin: str
    preset_value: Optional[object] = None
    tenant_value: Optional[object] = None


class PresetDifferenceOut(BaseModel):
    """What a preset would change, and what it would leave alone.

    The tenant's own configuration always wins: an entry in ``overwrites``
    is reported so that the customer can see the difference, and the
    customer's value is the one that stands.
    """

    preset_id: str
    preset_version: str
    adds: list[SettingChangeOut] = []
    unchanged: list[SettingChangeOut] = []
    overwrites: list[SettingChangeOut] = []
    undecided: list[SettingChangeOut] = []
    tenant_only: list[SettingChangeOut] = []
    modules_to_enable: list[str] = []
    modules_left_alone: list[str] = []
    exclusions: list[dict] = []
    provenance: list[ProvenanceOut] = []
    generated_at: str


class ReadinessFindingOut(BaseModel):
    """One thing the readiness check found."""

    rule_id: str
    category: str
    severity: str
    message: str
    fix_target: str
    entity: Optional[str] = None
    module: Optional[str] = None
    auto_fixable: bool = False


class ReadinessOut(BaseModel):
    """What is configured, what is missing, what is inconsistent and what is
    merely recommended."""

    preset_id: Optional[str] = None
    preset_version: Optional[str] = None
    configured: list[ReadinessFindingOut] = []
    missing: list[ReadinessFindingOut] = []
    inconsistent: list[ReadinessFindingOut] = []
    recommended: list[ReadinessFindingOut] = []
    findings: list[ReadinessFindingOut] = []
    generated_at: str
