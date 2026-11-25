/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ClockInRequest } from '../models/ClockInRequest';
import type { ClockOutRequest } from '../models/ClockOutRequest';
import type { EntryCorrectionRequest } from '../models/EntryCorrectionRequest';
import type { PaginatedTimeEntries } from '../models/PaginatedTimeEntries';
import type { PaginatedTimesheets } from '../models/PaginatedTimesheets';
import type { PaginatedWorkingTimeViolations } from '../models/PaginatedWorkingTimeViolations';
import type { TimeEntry } from '../models/TimeEntry';
import type { Timesheet } from '../models/Timesheet';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TimeService {
    /**
     * Start a working period
     * Starts a working period. Without `employee_id` the clock in is attributed to the caller; a manager or an administrator may clock somebody else in, and doing so for an employee outside the visibility scope of the caller returns 404. An employee that already has an open period returns 409 `conflict`.
     * @returns TimeEntry The working period was started.
     * @throws ApiError
     */
    public static timeClockIn({
        requestBody,
    }: {
        requestBody?: ClockInRequest,
    }): CancelablePromise<TimeEntry> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/time/clock-in',
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
     * Close a working period
     * Closes the open working period of the caller, or of the employee named by `employee_id` or `entry_id`. The period is closed at the server clock, not at a time sent by the client. An entry that is already closed returns 409 `conflict`; an entry in a locked period returns 409 `timesheet_locked`.
     * @returns TimeEntry The working period was closed.
     * @throws ApiError
     */
    public static timeClockOut({
        requestBody,
    }: {
        requestBody?: ClockOutRequest,
    }): CancelablePromise<TimeEntry> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/time/clock-out',
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
     * List the recorded working periods
     * Lists the working periods of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `employee_id` narrows it to one employee, `from` and `to` to a date range, and `source` to the way the entry was recorded. An employee outside the visibility scope of the caller is not returned.
     * @returns PaginatedTimeEntries A page of working periods.
     * @throws ApiError
     */
    public static timeListEntries({
        page = 1,
        pageSize = 50,
        employeeId,
        from,
        to,
        status,
        source,
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
         * Only entries of this employee. Defaults to the entries of the caller.
         */
        employeeId?: string,
        /**
         * Only entries on or after this date.
         */
        from?: string,
        /**
         * Only entries on or before this date.
         */
        to?: string,
        /**
         * Only entries in this state.
         */
        status?: 'open' | 'complete' | 'approved' | 'rejected',
        /**
         * Only entries recorded this way.
         */
        source?: 'terminal' | 'mobile' | 'manual' | 'import' | 'correction',
    }): CancelablePromise<PaginatedTimeEntries> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/time/entries',
            query: {
                'page': page,
                'page_size': pageSize,
                'employee_id': employeeId,
                'from': from,
                'to': to,
                'status': status,
                'source': source,
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
     * Ask for a working period to be corrected
     * Records a manual correction of a working period. The correction is never applied directly: the original entry keeps its values, the correction is recorded as a pending request and a manager has to approve it. The reason is mandatory and is kept on the audit trail. A correction on an entry in a locked period returns 409 `timesheet_locked`.
     * @returns TimeEntry The correction was recorded and is waiting for approval.
     * @throws ApiError
     */
    public static timeCreateEntryCorrection({
        entryId,
        requestBody,
    }: {
        /**
         * Identifier of the working period.
         */
        entryId: string,
        requestBody: EntryCorrectionRequest,
    }): CancelablePromise<TimeEntry> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/time/entries/{entry_id}/corrections',
            path: {
                'entry_id': entryId,
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
     * List timesheets
     * Lists the timesheets of this deployment. The list is paged; `page` and `page_size` control the window. `employee_id` narrows it to one employee, `period_start` and `period_end` to a period, and `status` to the state of the timesheet. A timesheet is only listed for the employee it belongs to and for the approvers of that employee.
     * @returns PaginatedTimesheets A page of timesheets.
     * @throws ApiError
     */
    public static timeListTimesheets({
        page = 1,
        pageSize = 50,
        employeeId,
        periodStart,
        periodEnd,
        status,
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
         * Only timesheets of this employee.
         */
        employeeId?: string,
        /**
         * Only timesheets whose period starts on or after this date.
         */
        periodStart?: string,
        /**
         * Only timesheets whose period ends on or before this date.
         */
        periodEnd?: string,
        /**
         * Only timesheets in this state.
         */
        status?: 'open' | 'submitted' | 'approved' | 'rejected' | 'locked',
    }): CancelablePromise<PaginatedTimesheets> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/time/timesheets',
            query: {
                'page': page,
                'page_size': pageSize,
                'employee_id': employeeId,
                'period_start': periodStart,
                'period_end': periodEnd,
                'status': status,
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
     * Approve a timesheet
     * Approves a submitted timesheet. The approver must be the manager of the employee or an administrator, and may not approve their own timesheet: doing so returns 403 `separation_of_duties`. A timesheet that is not submitted returns 409 `invalid_state_transition`, and a timesheet in a locked period returns 409 `timesheet_locked`.
     * @returns Timesheet The timesheet was approved.
     * @throws ApiError
     */
    public static timeApproveTimesheet({
        sheetId,
        comment,
    }: {
        /**
         * Identifier of the timesheet.
         */
        sheetId: string,
        /**
         * Note stored with the decision.
         */
        comment?: string,
    }): CancelablePromise<Timesheet> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/time/timesheets/{sheet_id}/approve',
            path: {
                'sheet_id': sheetId,
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
     * Submit a timesheet for approval
     * Submits the timesheet of one period for approval. The timesheet must be open or rejected; a timesheet that is already submitted or approved returns 409 `invalid_state_transition`. A timesheet in a period that a payroll cut off has locked returns 409 `timesheet_locked`.
     * @returns Timesheet The timesheet was submitted.
     * @throws ApiError
     */
    public static timeSubmitTimesheet({
        sheetId,
        comment,
    }: {
        /**
         * Identifier of the timesheet.
         */
        sheetId: string,
        /**
         * Note stored with the submission.
         */
        comment?: string,
    }): CancelablePromise<Timesheet> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/time/timesheets/{sheet_id}/submit',
            path: {
                'sheet_id': sheetId,
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
     * List the detected working time violations
     * Lists the breaches of the configured working time rules, for example a missing break or a daily maximum overrun. The list is paged; `page` and `page_size` control the window. `employee_id` narrows it to one employee, `from` and `to` to a date range and `severity` to the seriousness of the breach.
     * @returns PaginatedWorkingTimeViolations A page of violations.
     * @throws ApiError
     */
    public static timeListWorkingTimeViolations({
        page = 1,
        pageSize = 50,
        employeeId,
        from,
        to,
        severity,
        resolved,
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
         * Only violations of this employee.
         */
        employeeId?: string,
        /**
         * Only violations on or after this date.
         */
        from?: string,
        /**
         * Only violations on or before this date.
         */
        to?: string,
        /**
         * Only violations of this severity.
         */
        severity?: 'info' | 'warning' | 'critical',
        /**
         * Only resolved or only unresolved violations.
         */
        resolved?: boolean,
    }): CancelablePromise<PaginatedWorkingTimeViolations> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/time/working-time-violations',
            query: {
                'page': page,
                'page_size': pageSize,
                'employee_id': employeeId,
                'from': from,
                'to': to,
                'severity': severity,
                'resolved': resolved,
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
}
