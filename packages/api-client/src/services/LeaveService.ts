/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Holiday } from '../models/Holiday';
import type { HolidayBulkCreate } from '../models/HolidayBulkCreate';
import type { LeaveBalance } from '../models/LeaveBalance';
import type { LeaveLedgerEntry } from '../models/LeaveLedgerEntry';
import type { LeaveRequest } from '../models/LeaveRequest';
import type { LeaveRequestCreate } from '../models/LeaveRequestCreate';
import type { LeaveType } from '../models/LeaveType';
import type { PaginatedHolidays } from '../models/PaginatedHolidays';
import type { PaginatedLeaveRequests } from '../models/PaginatedLeaveRequests';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class LeaveService {
    /**
     * Read the leave balances
     * Returns the leave balance of every employee, or of the employees selected by the filters, for one leave type and one year. The balances are a projection of the ledger; the ledger itself is at `GET /leave/balances/{employee_id}/ledger`. `employee_id` defaults to the caller. A year outside the configured range returns 422 `validation_error`.
     * @returns LeaveBalance The leave balances.
     * @throws ApiError
     */
    public static leaveGetBalances({
        employeeId,
        leaveTypeId,
        year,
        departmentId,
    }: {
        /**
         * The employee to report on. Defaults to the caller.
         */
        employeeId?: string,
        /**
         * Only the balance of this leave type.
         */
        leaveTypeId?: string,
        /**
         * The year the balance is reported for. Defaults to the current year.
         */
        year?: number,
        /**
         * Only the balances of the employees of this department.
         */
        departmentId?: string,
    }): CancelablePromise<Array<LeaveBalance>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/leave/balances',
            query: {
                'employee_id': employeeId,
                'leave_type_id': leaveTypeId,
                'year': year,
                'department_id': departmentId,
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
    /**
     * Read the leave ledger of an employee
     * Returns the immutable movements of the leave balance of one employee: accruals, usages, adjustments, carry forwards and expiries, oldest first. Every row carries the running balance after the movement, so the balance can be recomputed from the ledger alone. Rows are never edited or deleted; a correcting movement is appended.
     * @returns LeaveLedgerEntry The ledger rows of the employee.
     * @throws ApiError
     */
    public static leaveGetBalanceLedger({
        employeeId,
        leaveTypeId,
        year,
        from,
        to,
    }: {
        /**
         * Identifier of the employee.
         */
        employeeId: string,
        /**
         * Only the movements of this leave type.
         */
        leaveTypeId?: string,
        /**
         * Only the movements of this year.
         */
        year?: number,
        /**
         * Only movements effective on or after this date.
         */
        from?: string,
        /**
         * Only movements effective on or before this date.
         */
        to?: string,
    }): CancelablePromise<Array<LeaveLedgerEntry>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/leave/balances/{employee_id}/ledger',
            path: {
                'employee_id': employeeId,
            },
            query: {
                'leave_type_id': leaveTypeId,
                'year': year,
                'from': from,
                'to': to,
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
    /**
     * List the non working days
     * Lists the non working days of this deployment. The list is paged; `page` and `page_size` control the window. `location_id` narrows it to one location and `year` to one year. The dates themselves are the customer's own: the platform never ships statutory dates.
     * @returns PaginatedHolidays A page of non working days.
     * @throws ApiError
     */
    public static leaveListHolidays({
        page = 1,
        pageSize = 50,
        locationId,
        year,
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
         * Only the non working days of this location.
         */
        locationId?: string,
        /**
         * Only the non working days of this year.
         */
        year?: number,
    }): CancelablePromise<PaginatedHolidays> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/leave/holidays',
            query: {
                'page': page,
                'page_size': pageSize,
                'location_id': locationId,
                'year': year,
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
     * Add the non working days of a location and a year
     * Adds a set of non working days for one location and one year in a single transaction: either all of them are stored or none is. A date that is already a non working day of that location is left alone and counted as unchanged. A date outside the given year returns 422 `validation_error`.
     * @returns Holiday The non working days were added.
     * @throws ApiError
     */
    public static leaveCreateHolidays({
        requestBody,
    }: {
        requestBody: HolidayBulkCreate,
    }): CancelablePromise<Array<Holiday>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/leave/holidays',
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
     * List leave requests
     * Lists the leave requests of this deployment, newest first. The list is paged; `page` and `page_size` control the window. Without `employee_id` the list holds the requests of every employee the caller may see: an employee sees their own requests, a manager the requests of their team. `status` narrows it to one decision state.
     * @returns PaginatedLeaveRequests A page of leave requests.
     * @throws ApiError
     */
    public static leaveListRequests({
        page = 1,
        pageSize = 50,
        employeeId,
        leaveTypeId,
        status,
        from,
        to,
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
         * Only the requests of this employee.
         */
        employeeId?: string,
        /**
         * Only requests of this leave type.
         */
        leaveTypeId?: string,
        /**
         * Only requests in this state.
         */
        status?: 'pending' | 'approved' | 'rejected' | 'cancelled',
        /**
         * Only requests that start on or after this date.
         */
        from?: string,
        /**
         * Only requests that end on or before this date.
         */
        to?: string,
    }): CancelablePromise<PaginatedLeaveRequests> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/leave/requests',
            query: {
                'page': page,
                'page_size': pageSize,
                'employee_id': employeeId,
                'leave_type_id': leaveTypeId,
                'status': status,
                'from': from,
                'to': to,
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
     * Request leave
     * Files a leave request for the caller, or for an employee the caller is allowed to file for. The quantity is derived from the leave calendar of the employee when it is not supplied. A request that overlaps an existing pending or approved request returns 409 `leave_overlaps_existing`; a request for more than the balance allows returns 409 `leave_insufficient_balance`; a request for a leave type that is not active returns 422 `validation_error`. The balance is reserved when the request is filed, not when it is approved.
     * @returns LeaveRequest The request was filed.
     * @throws ApiError
     */
    public static leaveCreateRequest({
        requestBody,
    }: {
        requestBody: LeaveRequestCreate,
    }): CancelablePromise<LeaveRequest> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/leave/requests',
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
     * Approve a leave request
     * Approves a pending leave request. The approver must be the manager of the employee or an administrator, and may not approve their own request: that returns 403 `separation_of_duties`. A request that is not pending returns 409 `invalid_state_transition`. On approval the reserved leave is taken from the balance and written to the ledger.
     * @returns LeaveRequest The request was approved.
     * @throws ApiError
     */
    public static leaveApproveRequest({
        requestId,
        comment,
    }: {
        /**
         * Identifier of the leave request.
         */
        requestId: string,
        /**
         * Note stored with the decision.
         */
        comment?: string,
    }): CancelablePromise<LeaveRequest> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/leave/requests/{request_id}/approve',
            path: {
                'request_id': requestId,
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
     * Cancel a leave request
     * Cancels a pending leave request. A request that was already decided, or one whose period a payroll cut off has already used, returns 409 `invalid_state_transition`. The reserved balance is released when the request is cancelled.
     * @returns LeaveRequest The request was cancelled.
     * @throws ApiError
     */
    public static leaveCancelRequest({
        requestId,
        reason,
    }: {
        /**
         * Identifier of the leave request.
         */
        requestId: string,
        /**
         * Note stored with the cancellation.
         */
        reason?: string,
    }): CancelablePromise<LeaveRequest> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/leave/requests/{request_id}/cancel',
            path: {
                'request_id': requestId,
            },
            query: {
                'reason': reason,
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
     * Reject a leave request
     * Rejects a pending leave request. A request that is not pending returns 409 `invalid_state_transition`. On rejection the reserved leave is released and a ledger movement is written.
     * @returns LeaveRequest The request was rejected.
     * @throws ApiError
     */
    public static leaveRejectRequest({
        requestId,
        comment,
    }: {
        /**
         * Identifier of the leave request.
         */
        requestId: string,
        /**
         * Note stored with the decision.
         */
        comment?: string,
    }): CancelablePromise<LeaveRequest> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/leave/requests/{request_id}/reject',
            path: {
                'request_id': requestId,
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
     * List the leave types
     * Lists the leave types configured for this deployment. The list is not paged: a deployment has a small, bounded number of leave types.
     * @returns LeaveType The leave types.
     * @throws ApiError
     */
    public static leaveListTypes({
        active,
    }: {
        /**
         * Only active or only inactive leave types.
         */
        active?: boolean,
    }): CancelablePromise<Array<LeaveType>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/leave/types',
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
}
