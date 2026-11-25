# E2E Scenarios

Each scenario: preconditions, steps, expected outcome, status.

1. Recruitment -> onboarding: precond seeded tenant; steps create req/candidate/offer/onboarding; expected employee created. Status: testable (backend suites exist); UI deferred where noted.
2. Lifecycle change: precond employee; steps promotion/transfer; expected history updated. Status: testable.
3. Attendance -> payroll: precond shifts/time entries; steps run payroll; expected payslip values. Status: testable (FY25-26 dry-run only).
4. Leave -> approval -> payroll impact: precond leave types; steps apply/approve; expected balance + payroll adjustment. Status: testable.
5. Payroll calc -> approval -> payslip: precond pay profiles; steps calculate/approve; expected payslip. Status: testable dry-run only (no statutory sign-off).
6. ESS self-service -> HR approval: precond associate account; steps submit request; expected HR approval. Status: testable.
7. Expenses: UI deferred; backend may be testable.
8. Performance -> learning: precond goals; steps review/assign learning; expected records. Status: testable.
9. Exit -> clearance -> F&F: gated; requires offboarding config. Status: deferred/blocked pending config.
10. HR case -> resolution: precond case; steps create/resolve; expected closed case. Status: testable.
11. Asset assign -> recover: precond asset; steps assign/recover; expected status. Status: testable.
