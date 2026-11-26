import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/context/AuthContext"
import { ErrorProvider, useError } from "@/context/ErrorContext"
import { TenantProvider } from "@/context/TenantContext"
import { Suspense, lazy } from "react"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { TenantLayout } from "@/components/TenantLayout"
import { PageSkeleton } from "@/components/ui/page-skeleton"
import { ThemeProvider } from "@/context/ThemeContext"
import { QueryProvider } from "@/components/QueryProvider"
import { Toaster } from "@/components/ui"

// Public pages (lazy loaded)
const Homepage = lazy(() => import("@/pages/Homepage"))
const Login = lazy(() => import("@/pages/Login"))
const ChangePassword = lazy(() => import("@/pages/ChangePassword"))
const ImportPage = lazy(() => import("@/pages/Import"))
const Mfa = lazy(() => import("@/pages/Mfa"))
const Jobs = lazy(() => import("@/pages/Jobs"))
const People = lazy(() => import("@/pages/People"))
const PlatformShowcase = lazy(() => import("@/pages/marketing/PlatformShowcase"))
const Compliance = lazy(() => import("@/pages/marketing/Compliance"))
const Solutions = lazy(() => import("@/pages/Solutions"))
const Industries = lazy(() => import("@/pages/marketing/Industries"))
const Resources = lazy(() => import("@/pages/Resources"))
const Pricing = lazy(() => import("@/pages/marketing/Pricing"))
const Security = lazy(() => import("@/pages/marketing/Security"))
const FAQ = lazy(() => import("@/pages/marketing/FAQ"))
const Compare = lazy(() => import("@/pages/marketing/Compare"))
const About = lazy(() => import("@/pages/About"))
const Careers = lazy(() => import("@/pages/Careers"))
const Contact = lazy(() => import("@/pages/Contact"))
const Privacy = lazy(() => import("@/pages/Privacy"))
const Terms = lazy(() => import("@/pages/Terms"))
const Documentation = lazy(() => import("@/pages/Documentation"))
const DesignShowcase = lazy(() => import("@/pages/Design"))
const AIPage = lazy(() => import("@/pages/marketing/AI"))
const IndustryDetail = lazy(() => import("@/pages/marketing/IndustryDetail"))

// Protected app pages (lazy loaded)
const Dashboard = lazy(() => import("@/pages/Dashboard"))
const Recruiting = lazy(() => import("@/pages/Recruiting"))
const Onboarding = lazy(() => import("@/pages/Onboarding"))
const TimeAttendance = lazy(() => import("@/pages/TimeAttendance"))
const Scheduling = lazy(() => import("@/pages/Scheduling"))
const RosterBuilder = lazy(() => import("@/pages/RosterBuilder"))
const Forecasting = lazy(() => import("@/pages/Forecasting"))
const ForecastRunDetail = lazy(() => import("@/pages/ForecastRunDetail"))
const Leave = lazy(() => import("@/pages/Leave"))
const LeaveLedger = lazy(() => import("@/pages/leave/LeaveLedger"))
const Expenses = lazy(() => import("@/pages/expenses/Expenses"))
const ExpenseDetail = lazy(() => import("@/pages/expenses/ExpenseDetail"))
const ExpenseNew = lazy(() => import("@/pages/expenses/ExpenseNew"))
const OnboardingConfig = lazy(() => import("@/pages/onboarding/OnboardingConfig"))
const Offboarding = lazy(() => import("@/pages/Offboarding"))
const Assets = lazy(() => import("@/pages/Assets"))
const MyAssets = lazy(() => import("@/pages/MyAssets"))
const Reports = lazy(() => import("@/pages/Reports"))
const ClientOnboarding = lazy(() => import("@/pages/ClientOnboarding"))
const Platform = lazy(() => import("@/pages/Platform"))
const PayRuns = lazy(() => import("@/pages/payroll/PayRuns"))
const PayRunDetail = lazy(() => import("@/pages/payroll/PayRunDetail"))
const PayrollSetup = lazy(() => import("@/pages/payroll/PayrollSetup"))
const PayrollOverview = lazy(() => import("@/pages/payroll/PayrollOverview"))
const LearningHub = lazy(() => import("@/pages/learning/LearningHub"))
const BenefitsHub = lazy(() => import("@/pages/benefits/BenefitsHub"))
const PerformanceHub = lazy(() => import("@/pages/performance/PerformanceHub"))
const ESSHub = lazy(() => import("@/pages/ess/ESSHub"))
const ProjectStatus = lazy(() => import("@/pages/ProjectStatus"))
const DesignGallery = lazy(() => import("@/pages/DesignGallery"))
const ThemeStudio = lazy(() => import("@/pages/ThemeStudio"))

// Admin pages (lazy loaded)
const IntegrationsHub = lazy(() => import("@/pages/admin/IntegrationsHub"))
const DataQuality = lazy(() => import("@/pages/admin/DataQuality"))
const UserAdmin = lazy(() => import("@/pages/admin/UserAdmin"))
const TenantBranding = lazy(() => import("@/pages/admin/TenantBranding"))
const ModuleEntitlements = lazy(() => import("@/pages/admin/ModuleEntitlements"))
const WorkflowApproval = lazy(() => import("@/pages/admin/WorkflowApproval"))
const IntegrationCredentials = lazy(() => import("@/pages/admin/IntegrationCredentials"))
const BackupRestore = lazy(() => import("@/pages/admin/BackupRestore"))
const FeatureFlags = lazy(() => import("@/pages/admin/FeatureFlags"))
const LocaleConfig = lazy(() => import("@/pages/admin/LocaleConfig"))
const RetentionExport = lazy(() => import("@/pages/admin/RetentionExport"))
const CandidateStages = lazy(() => import("@/pages/admin/CandidateStages"))
const AI04Summarisation = lazy(() => import("@/pages/admin/AI04Summarisation"))
const AIDrafting = lazy(() => import("@/pages/admin/AIDrafting"))
const AnnouncementsDirectory = lazy(() => import("@/pages/admin/AnnouncementsDirectory"))
const AttendancePolicies = lazy(() => import("@/pages/admin/AttendancePolicies"))
const AvailabilityLeave = lazy(() => import("@/pages/admin/AvailabilityLeave"))
const BankExport = lazy(() => import("@/pages/admin/BankExport"))
const Certifications = lazy(() => import("@/pages/admin/Certifications"))
const CompetencyCalibration = lazy(() => import("@/pages/admin/CompetencyCalibration"))
const ContingentWorkers = lazy(() => import("@/pages/admin/ContingentWorkers"))
const CoverageGaps = lazy(() => import("@/pages/admin/CoverageGaps"))
const CrossMidnightOvertime = lazy(() => import("@/pages/admin/CrossMidnightOvertime"))
const CustomFields = lazy(() => import("@/pages/admin/CustomFields"))
const DemandForecasting = lazy(() => import("@/pages/admin/DemandForecasting"))
const DemandStaffing = lazy(() => import("@/pages/admin/DemandStaffing"))
const DepartmentsCostCentres = lazy(() => import("@/pages/admin/DepartmentsCostCentres"))
const DocumentClassification = lazy(() => import("@/pages/admin/DocumentClassification"))
const DocumentsExpiry = lazy(() => import("@/pages/admin/DocumentsExpiry"))
const DocumentsLibrary = lazy(() => import("@/pages/documents/DocumentsLibrary"))
const ESSProfile = lazy(() => import("@/pages/admin/ESSProfile"))
const EarningsDeductions = lazy(() => import("@/pages/admin/EarningsDeductions"))
const ERCases = lazy(() => import("@/pages/er/ERCases"))
const EmployerContributions = lazy(() => import("@/pages/admin/EmployerContributions"))
const EmploymentStatus = lazy(() => import("@/pages/admin/EmploymentStatus"))
const EquipmentAccess = lazy(() => import("@/pages/admin/EquipmentAccess"))
const ExportErasure = lazy(() => import("@/pages/admin/ExportErasure"))
const ExternalIntegration = lazy(() => import("@/pages/admin/ExternalIntegration"))
const ForecastException = lazy(() => import("@/pages/admin/ForecastException"))
const FunnelAnalytics = lazy(() => import("@/pages/admin/FunnelAnalytics"))
const GapDetection = lazy(() => import("@/pages/admin/GapDetection"))
const GoalsOKR = lazy(() => import("@/pages/admin/GoalsOKR"))
const HRHelpCases = lazy(() => import("@/pages/admin/HRHelpCases"))
const HardConstraints = lazy(() => import("@/pages/admin/HardConstraints"))
const HeadcountCost = lazy(() => import("@/pages/admin/HeadcountCost"))
const HiringPlans = lazy(() => import("@/pages/admin/HiringPlans"))
const HistoricalRecord = lazy(() => import("@/pages/admin/HistoricalRecord"))
const ImprovementPlans = lazy(() => import("@/pages/admin/ImprovementPlans"))
const InformationCollection = lazy(() => import("@/pages/admin/InformationCollection"))
const InterviewScheduling = lazy(() => import("@/pages/admin/InterviewScheduling"))
const JurisdictionRules = lazy(() => import("@/pages/admin/JurisdictionRules"))
const KnowledgeBase = lazy(() => import("@/pages/admin/KnowledgeBase"))
const LearningAnalytics = lazy(() => import("@/pages/admin/LearningAnalytics"))
const LearningPaths = lazy(() => import("@/pages/admin/LearningPaths"))
const LeaveToPayroll = lazy(() => import("@/pages/admin/LeaveToPayroll"))
const LeaveTypes = lazy(() => import("@/pages/admin/LeaveTypes"))
const ManagerAssignments = lazy(() => import("@/pages/admin/ManagerAssignments"))
const ManagerAvailability = lazy(() => import("@/pages/admin/ManagerAvailability"))
const MentoringDevelopment = lazy(() => import("@/pages/admin/MentoringDevelopment"))
const MobileInteraction = lazy(() => import("@/pages/admin/MobileInteraction"))
const ModelVersioning = lazy(() => import("@/pages/admin/ModelVersioning"))
const MultiLocationAssignments = lazy(() => import("@/pages/admin/MultiLocationAssignments"))
const OfferApprovals = lazy(() => import("@/pages/admin/OfferApprovals"))
const OrgChart = lazy(() => import("@/pages/admin/OrgChart"))
const PaySchedule = lazy(() => import("@/pages/admin/PaySchedule"))
const PlanReconciliation = lazy(() => import("@/pages/admin/PlanReconciliation"))
const PlannedVsActual = lazy(() => import("@/pages/admin/PlannedVsActual"))
const PolicySearch = lazy(() => import("@/pages/admin/PolicySearch"))
const ProbationTracking = lazy(() => import("@/pages/admin/ProbationTracking"))
const ProcessAutomation = lazy(() => import("@/pages/admin/ProcessAutomation"))
const Prohibitions = lazy(() => import("@/pages/admin/Prohibitions"))
const PromotionReadiness = lazy(() => import("@/pages/admin/PromotionReadiness"))
const RehireHandling = lazy(() => import("@/pages/admin/RehireHandling"))
const RenewalReminders = lazy(() => import("@/pages/admin/RenewalReminders"))
const RequisitionStages = lazy(() => import("@/pages/admin/RequisitionStages"))
const ResumableChecklists = lazy(() => import("@/pages/admin/ResumableChecklists"))
const SalaryRevisions = lazy(() => import("@/pages/admin/SalaryRevisions"))
const SavedViews = lazy(() => import("@/pages/admin/SavedViews"))
const ScheduleViews = lazy(() => import("@/pages/admin/ScheduleViews"))
const ScheduledReporting = lazy(() => import("@/pages/admin/ScheduledReporting"))
const ShiftBasedAttendance = lazy(() => import("@/pages/admin/ShiftBasedAttendance"))
const SkillGaps = lazy(() => import("@/pages/admin/SkillGaps"))
const SkillTaxonomy = lazy(() => import("@/pages/admin/SkillTaxonomy"))
const SoftConstraints = lazy(() => import("@/pages/admin/SoftConstraints"))
const StatesDiscipline = lazy(() => import("@/pages/admin/StatesDiscipline"))
const SuccessionPlanning = lazy(() => import("@/pages/admin/SuccessionPlanning"))
const SwapsReplacements = lazy(() => import("@/pages/admin/SwapsReplacements"))
const TeamAvailability = lazy(() => import("@/pages/admin/TeamAvailability"))
const TemplatesDraftsPublish = lazy(() => import("@/pages/admin/TemplatesDraftsPublish"))
const TenStepJourney = lazy(() => import("@/pages/admin/TenStepJourney"))
const TimesheetLock = lazy(() => import("@/pages/admin/TimesheetLock"))
const Timesheets = lazy(() => import("@/pages/admin/Timesheets"))
const TrainingAssignments = lazy(() => import("@/pages/admin/TrainingAssignments"))
const TransferPromotion = lazy(() => import("@/pages/admin/TransferPromotion"))
const ValidationDuplicates = lazy(() => import("@/pages/admin/ValidationDuplicates"))
const BreakGlass = lazy(() => import("@/pages/admin/BreakGlass"))
const ComplianceCenter = lazy(() => import("@/pages/admin/ComplianceCenter"))

function AppRoutes() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
      {/* Public */}
      <Route path="/" element={<Homepage />} />
      <Route path="/platform" element={<ProtectedRoute><Platform /></ProtectedRoute>} />
      <Route path="/platform/compliance" element={<Compliance />} />
      <Route path="/platform/integrations" element={<ProtectedRoute><IntegrationsHub /></ProtectedRoute>} />
      <Route path="/login" element={<Login />} />
      <Route path="/change-password" element={<ProtectedRoute allowPasswordChange><ChangePassword /></ProtectedRoute>} />
      <Route path="/solutions" element={<Solutions />} />
      <Route path="/industries" element={<Industries />} />
      <Route path="/industries/:slug" element={<IndustryDetail />} />
      <Route path="/resources" element={<Resources />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/security" element={<Security />} />
      <Route path="/faq" element={<FAQ />} />
      <Route path="/compare/:competitor" element={<Compare />} />
      <Route path="/about" element={<About />} />
      <Route path="/careers" element={<Careers />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/docs" element={<Documentation />} />
      <Route path="/design" element={<ProtectedRoute><DesignShowcase /></ProtectedRoute>} />
      <Route path="/ai" element={<AIPage />} />

      {/* Protected app */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/people" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/people/departments" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/people/jobs" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/people/locations" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/people/positions" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/people/cost-centers" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/recruiting" element={<ProtectedRoute><Recruiting /></ProtectedRoute>} />
      <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
      <Route path="/time" element={<ProtectedRoute><TimeAttendance /></ProtectedRoute>} />
      <Route path="/scheduling" element={<ProtectedRoute><Scheduling /></ProtectedRoute>} />
      <Route path="/scheduling/roster" element={<ProtectedRoute><RosterBuilder /></ProtectedRoute>} />
      <Route path="/leave" element={<ProtectedRoute><Leave /></ProtectedRoute>} />
      <Route path="/leave/ledger" element={<ProtectedRoute><LeaveLedger /></ProtectedRoute>} />
      <Route path="/leave/ledger/:employeeId" element={<ProtectedRoute><LeaveLedger /></ProtectedRoute>} />
      <Route path="/onboarding-config" element={<ProtectedRoute><OnboardingConfig /></ProtectedRoute>} />
      <Route path="/offboarding" element={<ProtectedRoute><Offboarding /></ProtectedRoute>} />
      <Route path="/assets" element={<ProtectedRoute><Assets /></ProtectedRoute>} />
      <Route path="/my-assets" element={<ProtectedRoute><MyAssets /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
      <Route path="/client-onboarding" element={<ProtectedRoute><ClientOnboarding /></ProtectedRoute>} />
      <Route path="/platform/payroll" element={<ProtectedRoute><Platform /></ProtectedRoute>} />
      <Route path="/platform/payroll/overview" element={<ProtectedRoute><PayrollOverview /></ProtectedRoute>} />
      <Route path="/platform/payroll/runs" element={<ProtectedRoute><PayRuns /></ProtectedRoute>} />
      <Route path="/platform/payroll/runs/:runId" element={<ProtectedRoute><PayRunDetail /></ProtectedRoute>} />
      <Route path="/platform/payroll/setup" element={<ProtectedRoute><PayrollSetup /></ProtectedRoute>} />
      <Route path="/platform/performance" element={<ProtectedRoute><PerformanceHub /></ProtectedRoute>} />
      <Route path="/platform/benefits" element={<ProtectedRoute><BenefitsHub /></ProtectedRoute>} />
      <Route path="/platform/learning" element={<ProtectedRoute><LearningHub /></ProtectedRoute>} />
      <Route path="/ess" element={<ProtectedRoute><ESSHub /></ProtectedRoute>} />

      {/* Core app pages */}
      <Route path="/forecasting" element={<ProtectedRoute><Forecasting /></ProtectedRoute>} />
      <Route path="/forecasting/demand" element={<ProtectedRoute><Forecasting /></ProtectedRoute>} />
      <Route path="/forecasting/scenarios" element={<ProtectedRoute><Forecasting /></ProtectedRoute>} />
      <Route path="/forecasting/accuracy" element={<ProtectedRoute><Forecasting /></ProtectedRoute>} />
      <Route path="/forecasting/runs/:runId" element={<ProtectedRoute><ForecastRunDetail /></ProtectedRoute>} />
      <Route path="/project-status" element={<ProtectedRoute><ProjectStatus /></ProtectedRoute>} />
      <Route path="/theme" element={<ProtectedRoute><ThemeStudio /></ProtectedRoute>} />
      <Route path="/design-gallery" element={<ProtectedRoute><DesignGallery /></ProtectedRoute>} />
      <Route path="/data-quality" element={<ProtectedRoute><DataQuality /></ProtectedRoute>} />
      <Route path="/import" element={<ProtectedRoute><ImportPage /></ProtectedRoute>} />
      <Route path="/jobs" element={<ProtectedRoute><Jobs /></ProtectedRoute>} />
      <Route path="/mfa" element={<ProtectedRoute><Mfa /></ProtectedRoute>} />

      {/* Admin pages */}
      <Route path="/admin/users" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><UserAdmin /></ProtectedRoute>} />
      <Route path="/admin/branding" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TenantBranding /></ProtectedRoute>} />
      <Route path="/admin/entitlements" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ModuleEntitlements /></ProtectedRoute>} />
      <Route path="/admin/workflow" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><WorkflowApproval /></ProtectedRoute>} />
      <Route path="/admin/integrations" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><IntegrationCredentials /></ProtectedRoute>} />
      <Route path="/admin/backup" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><BackupRestore /></ProtectedRoute>} />
      <Route path="/admin/feature-flags" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><FeatureFlags /></ProtectedRoute>} />
      <Route path="/admin/locale" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LocaleConfig /></ProtectedRoute>} />
      <Route path="/admin/retention-export" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><RetentionExport /></ProtectedRoute>} />
      <Route path="/admin/candidate-stages" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CandidateStages /></ProtectedRoute>} />
      <Route path="/admin/rc-03" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CandidateStages /></ProtectedRoute>} />
      <Route path="/admin/project-status" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ProjectStatus /></ProtectedRoute>} />
      <Route path="/admin/design-gallery" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DesignGallery /></ProtectedRoute>} />
      <Route path="/admin/theme" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ThemeStudio /></ProtectedRoute>} />
      {/* Marketing aliases removed (admin-cleanup): same components reachable at
          /solutions /resources /about /careers /contact /privacy /terms /docs
          /pricing /security /faq /industries/:slug /compare/:competitor /design.
          /admin/platform-showcase kept — no non-admin route renders it. */
      <Route path="/admin/platform-showcase" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PlatformShowcase /></ProtectedRoute>} />

      {/* R6/R7/R8 Features */}
      <Route path="/admin/ad-03" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LocaleConfig /></ProtectedRoute>} />
      <Route path="/admin/ad-09" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><RetentionExport /></ProtectedRoute>} />
      <Route path="/admin/hr-01" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><People /></ProtectedRoute>} />
      <Route path="/admin/hr-05" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><MultiLocationAssignments /></ProtectedRoute>} />
      <Route path="/admin/lv-01" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LeaveTypes /></ProtectedRoute>} />
      <Route path="/admin/rc-05" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><OfferApprovals /></ProtectedRoute>} />
      <Route path="/admin/sc-04" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><HardConstraints /></ProtectedRoute>} />
      <Route path="/admin/sc-07" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CoverageGaps /></ProtectedRoute>} />
      <Route path="/admin/sc-10" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PlannedVsActual /></ProtectedRoute>} />
      <Route path="/admin/tm-02" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><AttendancePolicies /></ProtectedRoute>} />
      <Route path="/admin/tm-03" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CrossMidnightOvertime /></ProtectedRoute>} />
      <Route path="/admin/tm-04" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ShiftBasedAttendance /></ProtectedRoute>} />
      <Route path="/admin/tm-05" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TimesheetLock /></ProtectedRoute>} />
      <Route path="/admin/an-06" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PlanReconciliation /></ProtectedRoute>} />
      <Route path="/admin/bn-02" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><EmployerContributions /></ProtectedRoute>} />
      <Route path="/admin/ai-02" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DocumentClassification /></ProtectedRoute>} />
      <Route path="/admin/ob-04" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ProbationTracking /></ProtectedRoute>} />
      <Route path="/admin/ai-04" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><AI04Summarisation /></ProtectedRoute>} />
      <Route path="/admin/ai-03" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><AIDrafting /></ProtectedRoute>} />
      <Route path="/admin/announcements-directory" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><AnnouncementsDirectory /></ProtectedRoute>} />
      <Route path="/admin/attendance-policies" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><AttendancePolicies /></ProtectedRoute>} />
      <Route path="/admin/availability-leave" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><AvailabilityLeave /></ProtectedRoute>} />
      <Route path="/admin/backup-restore" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><BackupRestore /></ProtectedRoute>} />
      <Route path="/admin/bank-export" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><BankExport /></ProtectedRoute>} />
      <Route path="/admin/certifications" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><Certifications /></ProtectedRoute>} />
      <Route path="/admin/competency-calibration" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CompetencyCalibration /></ProtectedRoute>} />
      <Route path="/admin/contingent-workers" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ContingentWorkers /></ProtectedRoute>} />
      <Route path="/admin/coverage-gaps" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CoverageGaps /></ProtectedRoute>} />
      <Route path="/admin/cross-midnight-overtime" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CrossMidnightOvertime /></ProtectedRoute>} />
      <Route path="/admin/custom-fields" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><CustomFields /></ProtectedRoute>} />
      <Route path="/admin/data-quality" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DataQuality /></ProtectedRoute>} />
      <Route path="/admin/demand-forecasting" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DemandForecasting /></ProtectedRoute>} />
      <Route path="/admin/demand-staffing" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DemandStaffing /></ProtectedRoute>} />
      <Route path="/admin/departments-cost-centres" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DepartmentsCostCentres /></ProtectedRoute>} />
      <Route path="/admin/document-classification" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DocumentClassification /></ProtectedRoute>} />
      <Route path="/admin/documents-expiry" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DocumentsExpiry /></ProtectedRoute>} />
      <Route path="/admin/documents" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><DocumentsLibrary /></ProtectedRoute>} />
      <Route path="/admin/essprofile" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ESSProfile /></ProtectedRoute>} />
      <Route path="/admin/earnings-deductions" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><EarningsDeductions /></ProtectedRoute>} />
      <Route path="/admin/er-cases" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ERCases /></ProtectedRoute>} />
      <Route path="/admin/employer-contributions" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><EmployerContributions /></ProtectedRoute>} />
      <Route path="/admin/employment-status" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><EmploymentStatus /></ProtectedRoute>} />
      <Route path="/admin/equipment-access" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><EquipmentAccess /></ProtectedRoute>} />
      <Route path="/admin/export-erasure" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ExportErasure /></ProtectedRoute>} />
      <Route path="/admin/external-integration" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ExternalIntegration /></ProtectedRoute>} />
      <Route path="/admin/forecast-exception" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ForecastException /></ProtectedRoute>} />
      <Route path="/admin/funnel-analytics" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><FunnelAnalytics /></ProtectedRoute>} />
      <Route path="/admin/gap-detection" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><GapDetection /></ProtectedRoute>} />
      <Route path="/admin/goals-okr" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><GoalsOKR /></ProtectedRoute>} />
      <Route path="/admin/hrhelp-cases" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><HRHelpCases /></ProtectedRoute>} />
      <Route path="/admin/hard-constraints" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><HardConstraints /></ProtectedRoute>} />
      <Route path="/admin/headcount-cost" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><HeadcountCost /></ProtectedRoute>} />
      <Route path="/admin/hiring-plans" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><HiringPlans /></ProtectedRoute>} />
      <Route path="/admin/historical-record" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><HistoricalRecord /></ProtectedRoute>} />
      <Route path="/admin/improvement-plans" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ImprovementPlans /></ProtectedRoute>} />
      <Route path="/admin/information-collection" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><InformationCollection /></ProtectedRoute>} />
      <Route path="/admin/integration-credentials" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><IntegrationCredentials /></ProtectedRoute>} />
      <Route path="/admin/integrations-hub" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><IntegrationsHub /></ProtectedRoute>} />
      <Route path="/admin/interview-scheduling" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><InterviewScheduling /></ProtectedRoute>} />
      <Route path="/admin/jurisdiction-rules" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><JurisdictionRules /></ProtectedRoute>} />
      <Route path="/admin/knowledge-base" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><KnowledgeBase /></ProtectedRoute>} />
      <Route path="/admin/learning-analytics" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LearningAnalytics /></ProtectedRoute>} />
      <Route path="/admin/learning-paths" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LearningPaths /></ProtectedRoute>} />
      <Route path="/admin/leave-to-payroll" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LeaveToPayroll /></ProtectedRoute>} />
      <Route path="/admin/leave-types" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LeaveTypes /></ProtectedRoute>} />
      <Route path="/admin/locale-config" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><LocaleConfig /></ProtectedRoute>} />
      <Route path="/admin/manager-assignments" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ManagerAssignments /></ProtectedRoute>} />
      <Route path="/admin/manager-availability" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ManagerAvailability /></ProtectedRoute>} />
      <Route path="/admin/mentoring-development" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><MentoringDevelopment /></ProtectedRoute>} />
      <Route path="/admin/mobile-interaction" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><MobileInteraction /></ProtectedRoute>} />
      <Route path="/admin/model-versioning" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ModelVersioning /></ProtectedRoute>} />
      <Route path="/admin/module-entitlements" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ModuleEntitlements /></ProtectedRoute>} />
      <Route path="/admin/multi-location-assignments" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><MultiLocationAssignments /></ProtectedRoute>} />
      <Route path="/admin/offer-approvals" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><OfferApprovals /></ProtectedRoute>} />
      <Route path="/admin/org-chart" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><OrgChart /></ProtectedRoute>} />
      <Route path="/admin/pay-schedule" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PaySchedule /></ProtectedRoute>} />
      <Route path="/admin/plan-reconciliation" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PlanReconciliation /></ProtectedRoute>} />
      <Route path="/admin/planned-vs-actual" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PlannedVsActual /></ProtectedRoute>} />
      <Route path="/admin/policy-search" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PolicySearch /></ProtectedRoute>} />
      <Route path="/admin/probation-tracking" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ProbationTracking /></ProtectedRoute>} />
      <Route path="/admin/process-automation" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ProcessAutomation /></ProtectedRoute>} />
      <Route path="/admin/prohibitions" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><Prohibitions /></ProtectedRoute>} />
      <Route path="/admin/promotion-readiness" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><PromotionReadiness /></ProtectedRoute>} />
      <Route path="/admin/rehire-handling" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><RehireHandling /></ProtectedRoute>} />
      <Route path="/admin/renewal-reminders" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><RenewalReminders /></ProtectedRoute>} />
      <Route path="/admin/requisition-stages" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><RequisitionStages /></ProtectedRoute>} />
      <Route path="/admin/resumable-checklists" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ResumableChecklists /></ProtectedRoute>} />
      <Route path="/admin/salary-revisions" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SalaryRevisions /></ProtectedRoute>} />
      <Route path="/admin/saved-views" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SavedViews /></ProtectedRoute>} />
      <Route path="/admin/schedule-views" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ScheduleViews /></ProtectedRoute>} />
      <Route path="/admin/scheduled-reporting" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ScheduledReporting /></ProtectedRoute>} />
      <Route path="/admin/shift-based-attendance" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ShiftBasedAttendance /></ProtectedRoute>} />
      <Route path="/admin/skill-gaps" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SkillGaps /></ProtectedRoute>} />
      <Route path="/admin/skill-taxonomy" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SkillTaxonomy /></ProtectedRoute>} />
      <Route path="/admin/soft-constraints" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SoftConstraints /></ProtectedRoute>} />
      <Route path="/admin/states-discipline" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><StatesDiscipline /></ProtectedRoute>} />
      <Route path="/admin/succession-planning" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SuccessionPlanning /></ProtectedRoute>} />
      <Route path="/admin/swaps-replacements" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><SwapsReplacements /></ProtectedRoute>} />
      <Route path="/admin/team-availability" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TeamAvailability /></ProtectedRoute>} />
      <Route path="/admin/templates-drafts-publish" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TemplatesDraftsPublish /></ProtectedRoute>} />
      <Route path="/admin/ten-step-journey" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TenStepJourney /></ProtectedRoute>} />
      <Route path="/admin/tenant-branding" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TenantBranding /></ProtectedRoute>} />
      <Route path="/admin/timesheet-lock" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TimesheetLock /></ProtectedRoute>} />
      <Route path="/admin/timesheets" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><Timesheets /></ProtectedRoute>} />
      <Route path="/admin/training-assignments" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TrainingAssignments /></ProtectedRoute>} />
      <Route path="/admin/transfer-promotion" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><TransferPromotion /></ProtectedRoute>} />
      <Route path="/admin/user-admin" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><UserAdmin /></ProtectedRoute>} />
      <Route path="/admin/validation-duplicates" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ValidationDuplicates /></ProtectedRoute>} />
      <Route path="/admin/workflow-approval" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><WorkflowApproval /></ProtectedRoute>} />
      <Route path="/admin/break-glass" element={<ProtectedRoute roles={["SuperAdmin"]}><BreakGlass /></ProtectedRoute>} />
      <Route path="/admin/compliance" element={<ProtectedRoute roles={["SuperAdmin", "HR"]}><ComplianceCenter /></ProtectedRoute>} />

      {/* LP-EXP-001/002/003 — expenses (employee + approver UI, server-scoped) */}
      <Route path="/expenses" element={<ProtectedRoute><Expenses /></ProtectedRoute>} />
      <Route path="/expenses/new" element={<ProtectedRoute><ExpenseNew /></ProtectedRoute>} />
      <Route path="/expenses/:id" element={<ProtectedRoute><ExpenseDetail /></ProtectedRoute>} />

      {/* Tenant-scoped workplace routes */}
      <Route path="/t/:slug/*" element={<ProtectedRoute><TenantLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="people" element={<People />} />
        <Route path="people/departments" element={<People />} />
        <Route path="people/jobs" element={<People />} />
        <Route path="people/locations" element={<People />} />
        <Route path="people/positions" element={<People />} />
        <Route path="people/cost-centers" element={<People />} />
        <Route path="recruiting" element={<Recruiting />} />
        <Route path="onboarding" element={<Onboarding />} />
        <Route path="time" element={<TimeAttendance />} />
        <Route path="scheduling" element={<Scheduling />} />
        <Route path="scheduling/roster" element={<RosterBuilder />} />
        <Route path="leave" element={<Leave />} />
        <Route path="leave/ledger" element={<LeaveLedger />} />
        <Route path="leave/ledger/:employeeId" element={<LeaveLedger />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="expenses/new" element={<ExpenseNew />} />
        <Route path="expenses/:id" element={<ExpenseDetail />} />
        <Route path="onboarding-config" element={<OnboardingConfig />} />
        <Route path="offboarding" element={<Offboarding />} />
        <Route path="assets" element={<Assets />} />
        <Route path="my-assets" element={<MyAssets />} />
        <Route path="reports" element={<Reports />} />
        <Route path="client-onboarding" element={<ClientOnboarding />} />
        <Route path="platform/payroll" element={<Platform />} />
        <Route path="platform/payroll/runs" element={<PayRuns />} />
        <Route path="platform/payroll/runs/:runId" element={<PayRunDetail />} />
        <Route path="platform/payroll/setup" element={<PayrollSetup />} />
        <Route path="platform/performance" element={<PerformanceHub />} />
        <Route path="platform/benefits" element={<BenefitsHub />} />
        <Route path="platform/learning" element={<LearningHub />} />
        <Route path="ess" element={<ESSHub />} />
        <Route path="forecasting" element={<Forecasting />} />
        <Route path="project-status" element={<ProjectStatus />} />
        <Route path="theme" element={<ThemeStudio />} />
        <Route path="design-gallery" element={<DesignGallery />} />
        <Route path="data-quality" element={<DataQuality />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="mfa" element={<Mfa />} />
      </Route>


    </Routes>
    </Suspense>
  )
}

function App() {
  return (
    <ThemeProvider>
      <QueryProvider>
        <ErrorProvider>
          <TenantProvider>
            <AuthProvider>
              <BrowserRouter>
                <AppRoutes />
              </BrowserRouter>
            </AuthProvider>
          </TenantProvider>
        </ErrorProvider>
      </QueryProvider>
      <Toaster />
    </ThemeProvider>
  )
}

export default App
