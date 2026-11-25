/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CoverageResponse } from '../models/CoverageResponse';
import type { PaginatedRosterEntries } from '../models/PaginatedRosterEntries';
import type { PaginatedRosterVersions } from '../models/PaginatedRosterVersions';
import type { PaginatedShiftTemplates } from '../models/PaginatedShiftTemplates';
import type { RosterGenerateRequest } from '../models/RosterGenerateRequest';
import type { RosterGenerateResponse } from '../models/RosterGenerateResponse';
import type { RosterPublishRequest } from '../models/RosterPublishRequest';
import type { RosterVersion } from '../models/RosterVersion';
import type { ShiftTemplate } from '../models/ShiftTemplate';
import type { ShiftTemplateCreate } from '../models/ShiftTemplateCreate';
import type { Swap } from '../models/Swap';
import type { SwapRequest } from '../models/SwapRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SchedulingService {
    /**
     * Read the coverage against the demand
     * Returns how much of the demand of a location and a period the roster covers, and the gaps that remain. Coverage is computed against the published roster, or against the draft when `version_id` names one.
     * @returns CoverageResponse The coverage of the period.
     * @throws ApiError
     */
    public static schedulingGetCoverage({
        locationId,
        from,
        to,
        versionId,
    }: {
        /**
         * The location the coverage is computed for.
         */
        locationId: string,
        /**
         * First day of the range.
         */
        from: string,
        /**
         * Last day of the range.
         */
        to: string,
        /**
         * A specific roster version. Defaults to the published one.
         */
        versionId?: string,
    }): CancelablePromise<CoverageResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/scheduling/coverage',
            query: {
                'location_id': locationId,
                'from': from,
                'to': to,
                'version_id': versionId,
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
     * Read the roster
     * Returns the shifts of a location for a date range, from the published roster when there is one and from the draft version otherwise. `version_id` selects a specific version; without it the published version is used. The result is paged; `page` and `page_size` control the window.
     * @returns PaginatedRosterEntries A page of roster entries.
     * @throws ApiError
     */
    public static schedulingGetRoster({
        locationId,
        from,
        to,
        page = 1,
        pageSize = 50,
        versionId,
        employeeId,
    }: {
        /**
         * The location the roster is read for.
         */
        locationId: string,
        /**
         * First day of the range.
         */
        from: string,
        /**
         * Last day of the range.
         */
        to: string,
        /**
         * 1-based page number.
         */
        page?: number,
        /**
         * Rows per page. The server may return fewer rows than requested.
         */
        pageSize?: number,
        /**
         * A specific roster version. Defaults to the published one.
         */
        versionId?: string,
        /**
         * Only the shifts of this employee.
         */
        employeeId?: string,
    }): CancelablePromise<PaginatedRosterEntries> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/scheduling/roster',
            query: {
                'page': page,
                'page_size': pageSize,
                'location_id': locationId,
                'from': from,
                'to': to,
                'version_id': versionId,
                'employee_id': employeeId,
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
     * Produce a candidate roster
     * Runs the solver over the demand, the constraints and the weights and returns a candidate roster, the slots it could not fill and the metadata of the run. The candidate is a draft: it changes nothing until the version is published. A request whose demand and constraints contradict each other returns 422 `validation_error`; a request the solver cannot satisfy at all returns 422 `solver_infeasible`; a run that hits the time limit returns 503 `solver_timeout` with the list of the unmet slots.
     * @returns RosterGenerateResponse The candidate roster and the solver metadata.
     * @throws ApiError
     */
    public static schedulingGenerateRoster({
        requestBody,
    }: {
        requestBody: RosterGenerateRequest,
    }): CancelablePromise<RosterGenerateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/scheduling/roster/generate',
            body: requestBody,
            mediaType: 'application/json',
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
     * Publish a roster version
     * Publishes a candidate roster and makes it live. Every hard constraint is re-checked at this point, not only at generation time: a candidate that has gone stale, because a leave was approved or an employee left in the meantime, is refused with 409 `swap_violates_constraints` or 409 `roster_already_published`. The call is idempotent: the same idempotency key with the same payload returns the first result, the same key with another payload returns 409 `idempotency_key_reuse`, and a request with the same key that is still running returns 409 `request_in_flight`. A missing or malformed idempotency key returns 422 `invalid_idempotency_key`.
     * @returns RosterVersion The version was published.
     * @throws ApiError
     */
    public static schedulingPublishRoster({
        idempotencyKey,
        requestBody,
    }: {
        /**
         * Caller-generated key (1-200 characters) that makes this mutation safe to retry. Replaying the same key with the same payload returns the original result; replaying it with a different payload is a 409 `idempotency_key_reuse`.
         */
        idempotencyKey: string,
        requestBody: RosterPublishRequest,
    }): CancelablePromise<RosterVersion> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/scheduling/roster/publish',
            headers: {
                'Idempotency-Key': idempotencyKey,
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
     * List the roster versions
     * Lists the versions of the roster of a location, newest first. The list is paged; `page` and `page_size` control the window. A published version is immutable; a new version is created by publishing a new candidate.
     * @returns PaginatedRosterVersions A page of roster versions.
     * @throws ApiError
     */
    public static schedulingListRosterVersions({
        page = 1,
        pageSize = 50,
        locationId,
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
         * Only the versions of this location.
         */
        locationId?: string,
        /**
         * Only the versions in this state.
         */
        status?: 'draft' | 'published' | 'superseded',
    }): CancelablePromise<PaginatedRosterVersions> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/scheduling/roster/versions',
            query: {
                'page': page,
                'page_size': pageSize,
                'location_id': locationId,
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
     * List the shift templates
     * Lists the shift templates of this deployment. The list is paged; `page` and `page_size` control the window. `location_id` narrows it to one location. A template that a published roster already uses cannot be deleted, only superseded with a new version.
     * @returns PaginatedShiftTemplates A page of shift templates.
     * @throws ApiError
     */
    public static schedulingListShiftTemplates({
        page = 1,
        pageSize = 50,
        locationId,
        search,
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
         * Only the templates of this location.
         */
        locationId?: string,
        /**
         * Case insensitive match on the name of the template.
         */
        search?: string,
    }): CancelablePromise<PaginatedShiftTemplates> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/scheduling/shift-templates',
            query: {
                'page': page,
                'page_size': pageSize,
                'location_id': locationId,
                'search': search,
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
     * Create a shift template
     * Creates a shift template. A shift that ends earlier than it starts crosses midnight and is accepted, but only when `crosses_midnight` is set. A name that is already taken returns 409 `duplicate_natural_key`.
     * @returns ShiftTemplate The shift template was created.
     * @throws ApiError
     */
    public static schedulingCreateShiftTemplate({
        requestBody,
    }: {
        requestBody: ShiftTemplateCreate,
    }): CancelablePromise<ShiftTemplate> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/scheduling/shift-templates',
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
     * Ask for a shift to be handed over
     * Files a request to hand a shift of the published roster to another employee. The request is checked against the hard constraints before it is filed: a swap that would break one returns 409 `swap_violates_constraints` with the list of the broken constraints. The shift stays with its current owner until the swap is approved.
     * @returns Swap The swap request was filed.
     * @throws ApiError
     */
    public static schedulingCreateSwap({
        requestBody,
    }: {
        requestBody: SwapRequest,
    }): CancelablePromise<Swap> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/scheduling/swaps',
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
     * Approve a shift swap
     * Approves a pending shift swap and moves the shift to the other employee. The hard constraints are checked again here: a swap that has become invalid returns 409 `swap_violates_constraints`. A swap that is not pending returns 409 `invalid_state_transition`. A published roster version that is already locked by a payroll cut off cannot be changed and returns 409 `roster_already_published`.
     * @returns Swap The swap was approved.
     * @throws ApiError
     */
    public static schedulingApproveSwap({
        swapId,
        comment,
    }: {
        /**
         * Identifier of the swap request.
         */
        swapId: string,
        /**
         * Note stored with the decision.
         */
        comment?: string,
    }): CancelablePromise<Swap> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/scheduling/swaps/{swap_id}/approve',
            path: {
                'swap_id': swapId,
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
}
