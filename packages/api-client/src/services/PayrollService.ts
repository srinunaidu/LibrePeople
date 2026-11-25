/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginatedPayRuns } from '../models/PaginatedPayRuns';
import type { PaginatedPayslips } from '../models/PaginatedPayslips';
import type { PayComponent } from '../models/PayComponent';
import type { PaymentFile } from '../models/PaymentFile';
import type { PayProfile } from '../models/PayProfile';
import type { PayRun } from '../models/PayRun';
import type { PayRunCalculateRequest } from '../models/PayRunCalculateRequest';
import type { PayRunCreate } from '../models/PayRunCreate';
import type { Payslip } from '../models/Payslip';
import type { ReconciliationReport } from '../models/ReconciliationReport';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PayrollService {
    /**
     * List the pay components
     * Lists the pay components of this deployment: the earnings, the deductions and the employer contributions that a pay profile is built from. The calculation formula of a component is owned by the customer; the platform does not publish statutory values.
     * @returns PayComponent The pay components.
     * @throws ApiError
     */
    public static payrollListPayComponents({
        category,
        search,
    }: {
        /**
         * Only the components of this category.
         */
        category?: 'earning' | 'deduction' | 'employer_contribution',
        /**
         * Case insensitive match on the code and the name.
         */
        search?: string,
    }): CancelablePromise<Array<PayComponent>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/pay-components',
            query: {
                'category': category,
                'search': search,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * List the pay profiles
     * Lists the pay profiles of this deployment. A profile is the named set of components a pay run uses, together with the currency and the pay frequency of the run.
     * @returns PayProfile The pay profiles.
     * @throws ApiError
     */
    public static payrollListPayProfiles({
        active,
    }: {
        /**
         * Only active or only inactive profiles.
         */
        active?: boolean,
    }): CancelablePromise<Array<PayProfile>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/pay-profiles',
            query: {
                'active': active,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * List the payslips
     * Lists the payslips of this deployment. The list is paged; `page` and `page_size` control the window. `run_id` and `employee_id` narrow it down. An employee sees only their own payslips. The amounts of a run that is not finalised are provisional.
     * @returns PaginatedPayslips A page of payslips.
     * @throws ApiError
     */
    public static payrollListPayslips({
        page = 1,
        pageSize = 50,
        runId,
        employeeId,
        periodId,
    }: {
        /**
         * 1-based page number.
         */
        page?: number,
        /**
         * Rows per page. The server may return fewer rows than requested.
         */
        pageSize?: number,
        /**
         * Only the payslips of this run.
         */
        runId?: string,
        /**
         * Only the payslips of this employee.
         */
        employeeId?: string,
        /**
         * Only the payslips of this pay period.
         */
        periodId?: string,
    }): CancelablePromise<PaginatedPayslips> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/payslips',
            query: {
                'page': page,
                'page_size': pageSize,
                'run_id': runId,
                'employee_id': employeeId,
                'period_id': periodId,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read one payslip
     * Returns one payslip with its lines. The payslip of an employee outside the visibility scope of the caller returns 404, never 403. The amounts of a run that is not finalised are provisional and are marked as such by the state of the run.
     * @returns Payslip The payslip.
     * @throws ApiError
     */
    public static payrollGetPayslip({
        payslipId,
    }: {
        /**
         * Identifier of the payslip.
         */
        payslipId: string,
    }): CancelablePromise<Payslip> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/payslips/{payslip_id}',
            path: {
                'payslip_id': payslipId,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * List the pay runs
     * Lists the pay runs of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `status` and `period_id` narrow it down. Only runs the caller may see are returned.
     * @returns PaginatedPayRuns A page of pay runs.
     * @throws ApiError
     */
    public static payrollListRuns({
        page = 1,
        pageSize = 50,
        status,
        periodId,
        jurisdiction,
    }: {
        /**
         * 1-based page number.
         */
        page?: number,
        /**
         * Rows per page. The server may return fewer rows than requested.
         */
        pageSize?: number,
        /**
         * Only the runs in this state.
         */
        status?: 'draft' | 'calculated' | 'approved' | 'finalised',
        /**
         * Only the runs of this pay period.
         */
        periodId?: string,
        /**
         * Only the runs of this jurisdiction.
         */
        jurisdiction?: string,
    }): CancelablePromise<PaginatedPayRuns> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/runs',
            query: {
                'page': page,
                'page_size': pageSize,
                'status': status,
                'period_id': periodId,
                'jurisdiction': jurisdiction,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Create a draft pay run
     * Creates a pay run in the `draft` state for one pay period and one jurisdiction. Nothing is calculated here. A jurisdiction that has no rule pack at all returns 422 `rule_pack_missing`; a jurisdiction whose pack exists but is not `verified` is accepted, because the block belongs to the calculation step, not to the creation step. A second run for the same period and jurisdiction returns 409 `duplicate_natural_key`.
     * @returns PayRun The draft run was created.
     * @throws ApiError
     */
    public static payrollCreateRun({
        requestBody,
    }: {
        requestBody: PayRunCreate,
    }): CancelablePromise<PayRun> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/payroll/runs',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Approve a pay run
     * Approves a calculated run and moves it to `approved`. The approver must hold the payroll approval role and may not approve a run they prepared themselves: that returns 403 `separation_of_duties`. A run that is not calculated returns 409 `invalid_state_transition`.
     * @returns PayRun The run was approved.
     * @throws ApiError
     */
    public static payrollApproveRun({
        runId,
        comment,
    }: {
        /**
         * Identifier of the pay run.
         */
        runId: string,
        /**
         * Note stored with the approval.
         */
        comment?: string,
    }): CancelablePromise<PayRun> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/payroll/runs/{run_id}/approve',
            path: {
                'run_id': runId,
            },
            query: {
                'comment': comment,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Calculate a pay run
     * Computes the run. With `dry_run` true (the default) the run is computed and nothing is written; with `dry_run` false the result is persisted and the run moves to `calculated`.
     * The calculation is refused for a jurisdiction whose rule pack is not `verified`: the response is 422 `rule_pack_not_verified` with the jurisdiction and the list of the checks that have to pass, and nothing is computed. A jurisdiction with no pack at all returns 422 `rule_pack_missing`. A run that is already `approved` or `finalised` returns 409 `invalid_state_transition`, and a run that was changed since it was read returns 409 `concurrent_update`. A rule pack that fails its own load returns 503 `rule_pack_loader_failure`.
     * @returns PayRun The run was calculated.
     * @throws ApiError
     */
    public static payrollCalculateRun({
        runId,
        requestBody,
    }: {
        /**
         * Identifier of the pay run.
         */
        runId: string,
        requestBody?: PayRunCalculateRequest,
    }): CancelablePromise<PayRun> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/payroll/runs/{run_id}/calculate',
            path: {
                'run_id': runId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Finalise a pay run
     * Finalises an approved run. From this moment the run and its payslips are immutable: any later attempt to change them returns 409 `pay_run_already_finalised`. Finalising without an approval returns 409 `invalid_state_transition`. The payslips are issued and the payment file becomes available.
     * @returns PayRun The run was finalised.
     * @throws ApiError
     */
    public static payrollFinaliseRun({
        runId,
        comment,
    }: {
        /**
         * Identifier of the pay run.
         */
        runId: string,
        /**
         * Note stored with the finalisation.
         */
        comment?: string,
    }): CancelablePromise<PayRun> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/payroll/runs/{run_id}/finalise',
            path: {
                'run_id': runId,
            },
            query: {
                'comment': comment,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Export the payment file of a pay run
     * Returns the description of the payment file of a finalised run. The file itself is fetched from the short lived download URL; the bytes are never inlined in this response. A run that is not finalised has no payment file and returns 409 `invalid_state_transition`. Exports are rate limited: too many exports in a period returns 429 `export_quota_exceeded`.
     * @returns PaymentFile The payment file description and its download URL.
     * @throws ApiError
     */
    public static payrollGetPaymentFile({
        runId,
        format,
    }: {
        /**
         * Identifier of the pay run.
         */
        runId: string,
        /**
         * The file format. Defaults to the format of the run.
         */
        format?: 'csv' | 'camt053' | 'sepa' | 'ach',
    }): CancelablePromise<PaymentFile> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/runs/{run_id}/payment-file',
            path: {
                'run_id': runId,
            },
            query: {
                'format': format,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                429: `The caller exceeded a rate limit. The body carries the \`rate_limit\` category and the \`Retry-After\` header states how long to wait.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read the reconciliation of a pay run
     * Returns the reconciliation of a run: the totals against the source data, the breakdown per component, the variances that need a human look and the checks that were run. The reconciliation is available for a calculated run; for a draft run it is empty.
     * @returns ReconciliationReport The reconciliation report.
     * @throws ApiError
     */
    public static payrollGetReconciliation({
        runId,
    }: {
        /**
         * Identifier of the pay run.
         */
        runId: string,
    }): CancelablePromise<ReconciliationReport> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/payroll/runs/{run_id}/reconciliation',
            path: {
                'run_id': runId,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
}
