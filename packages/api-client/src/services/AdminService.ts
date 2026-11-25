/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuditVerification } from '../models/AuditVerification';
import type { DsarExport } from '../models/DsarExport';
import type { DsarExportCreate } from '../models/DsarExportCreate';
import type { ErasureRequest } from '../models/ErasureRequest';
import type { ErasureRequestCreate } from '../models/ErasureRequestCreate';
import type { Job } from '../models/Job';
import type { PaginatedAuditEntries } from '../models/PaginatedAuditEntries';
import type { PaginatedDsarExports } from '../models/PaginatedDsarExports';
import type { PaginatedErasureRequests } from '../models/PaginatedErasureRequests';
import type { PaginatedJobs } from '../models/PaginatedJobs';
import type { PaginatedRulePacks } from '../models/PaginatedRulePacks';
import type { RetentionSchedule } from '../models/RetentionSchedule';
import type { RetentionScheduleUpdate } from '../models/RetentionScheduleUpdate';
import type { RulePack } from '../models/RulePack';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminService {
    /**
     * Read the audit log
     * Reads the audit log of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `action`, `entity_type`, `entity_id`, `actor` and `from`/`to` narrow it down. Every entry carries the hash of the previous entry, so the log is a chain: a removed or edited row breaks the chain at that point. The chain can be checked with `GET /admin/audit/verify`.
     * @returns PaginatedAuditEntries A page of audit entries.
     * @throws ApiError
     */
    public static adminListAudit({
        page = 1,
        pageSize = 50,
        action,
        entityType,
        entityId,
        actor,
        from,
        to,
        verify = false,
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
         * Only the entries with this action, for example `leave.approve`.
         */
        action?: string,
        /**
         * Only the entries about this entity type.
         */
        entityType?: string,
        /**
         * Only the entries about this entity.
         */
        entityId?: string,
        /**
         * Only the entries written by this user.
         */
        actor?: string,
        /**
         * Only the entries from this moment on.
         */
        from?: string,
        /**
         * Only the entries up to this moment.
         */
        to?: string,
        /**
         * Also report whether the chain still holds. The verification result is reported in `meta` and does not change the entries that are returned.
         */
        verify?: boolean,
    }): CancelablePromise<PaginatedAuditEntries> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/audit',
            query: {
                'page': page,
                'page_size': pageSize,
                'action': action,
                'entity_type': entityType,
                'entity_id': entityId,
                'actor': actor,
                'from': from,
                'to': to,
                'verify': verify,
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
     * Verify the audit chain
     * Walks the audit chain of this deployment and checks that every entry still hashes to the value it carries, including the hash of the entry before it. The response says whether the chain holds and how many entries were checked. When it does not hold, the first broken link is reported with its position and the reason, for example `hash_mismatch` or `missing_predecessor`. The verification is read only: it never repairs the chain.
     * @returns AuditVerification The result of the verification.
     * @throws ApiError
     */
    public static adminVerifyAudit(): CancelablePromise<AuditVerification> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/audit/verify',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * List the data subject access exports
     * Lists the data subject access exports of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `status` and `subject_type` narrow it down. The download URL of a ready export is short lived; it is not part of the list entry.
     * @returns PaginatedDsarExports A page of exports.
     * @throws ApiError
     */
    public static adminListDsarExports({
        page = 1,
        pageSize = 50,
        status,
        subjectType,
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
         * Only the exports in this state.
         */
        status?: 'queued' | 'building' | 'ready' | 'expired' | 'failed',
        /**
         * Only the exports about this kind of subject.
         */
        subjectType?: 'employee' | 'applicant' | 'contractor',
    }): CancelablePromise<PaginatedDsarExports> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/dsar-exports',
            query: {
                'page': page,
                'page_size': pageSize,
                'status': status,
                'subject_type': subjectType,
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
     * Start a data subject access export
     * Starts building the export of everything the platform holds about one subject. The work is done by a background job; the export is ready for download when the job has finished. A subject that does not exist returns 404 `employee_not_found`. The export is written to the object storage with a short lived URL and it expires.
     * @returns DsarExport The export was started.
     * @throws ApiError
     */
    public static adminCreateDsarExport({
        requestBody,
    }: {
        requestBody: DsarExportCreate,
    }): CancelablePromise<DsarExport> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/admin/dsar-exports',
            body: requestBody,
            mediaType: 'application/json',
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
     * List the erasure requests
     * Lists the erasure requests of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `status` and `subject_type` narrow it down. A request that is being processed is held by a background job.
     * @returns PaginatedErasureRequests A page of erasure requests.
     * @throws ApiError
     */
    public static adminListErasureRequests({
        page = 1,
        pageSize = 50,
        status,
        subjectType,
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
         * Only the requests in this state.
         */
        status?: 'open' | 'processing' | 'completed' | 'rejected',
        /**
         * Only the requests about this kind of subject.
         */
        subjectType?: 'employee' | 'applicant' | 'contractor',
    }): CancelablePromise<PaginatedErasureRequests> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/erasure-requests',
            query: {
                'page': page,
                'page_size': pageSize,
                'status': status,
                'subject_type': subjectType,
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
     * File an erasure request
     * Files a request to erase the personal data of one subject. The work is done by a background job. Records that are under a legal hold are not erased: they are reported in the job result and the request stays open. A subject that does not exist returns 404 `employee_not_found`; a request without the legal basis it needs returns 422 `validation_error`.
     * @returns ErasureRequest The erasure request was filed.
     * @throws ApiError
     */
    public static adminCreateErasureRequest({
        requestBody,
    }: {
        requestBody: ErasureRequestCreate,
    }): CancelablePromise<ErasureRequest> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/admin/erasure-requests',
            body: requestBody,
            mediaType: 'application/json',
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
     * List the background jobs
     * Lists the background jobs of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `state` narrows it to one lifecycle state and `type` to one job type. A job that exhausted its attempts is in the `dead` state and stays visible here: a dead job is never silently discarded.
     * @returns PaginatedJobs A page of background jobs.
     * @throws ApiError
     */
    public static adminListJobs({
        page = 1,
        pageSize = 50,
        state,
        type,
        includePayload = false,
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
         * Only the jobs in this state.
         */
        state?: 'pending' | 'running' | 'succeeded' | 'failed' | 'dead' | 'cancelled' | 'discarded',
        /**
         * Only the jobs of this type.
         */
        type?: string,
        /**
         * Include the payload of the job. Off by default.
         */
        includePayload?: boolean,
    }): CancelablePromise<PaginatedJobs> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/jobs',
            query: {
                'page': page,
                'page_size': pageSize,
                'state': state,
                'type': type,
                'include_payload': includePayload,
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
     * Read one background job
     * Returns one background job with its state, its attempt count and, when it failed, the error it failed with. The error of a job uses the same code vocabulary as the HTTP API, so a client can branch on it. A job that does not exist returns 404 `job_not_found`.
     * @returns Job The job.
     * @throws ApiError
     */
    public static adminGetJob({
        jobId,
    }: {
        /**
         * Identifier of the job.
         */
        jobId: string,
    }): CancelablePromise<Job> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/jobs/{job_id}',
            path: {
                'job_id': jobId,
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
     * Discard a background job
     * Marks a job as discarded so that it is not picked up again. The record of the job is kept: discarding removes the work, never the evidence. A job that is still running returns 409 `invalid_state_transition`. The discard is written to the audit log with the reason.
     * @returns Job The job was discarded.
     * @throws ApiError
     */
    public static adminDiscardJob({
        jobId,
        reason,
    }: {
        /**
         * Identifier of the job.
         */
        jobId: string,
        /**
         * Why the job is discarded. Stored on the audit log.
         */
        reason?: string,
    }): CancelablePromise<Job> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/admin/jobs/{job_id}/discard',
            path: {
                'job_id': jobId,
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
     * Retry a background job
     * Puts a failed or dead job back into the queue. The attempt counter is not reset, so the configured maximum still applies. A job that is still running returns 409 `invalid_state_transition`; a job that another worker has already taken over returns 409 `lease_lost`. Retrying a job that has already succeeded is a no op.
     * @returns Job The job was put back into the queue.
     * @throws ApiError
     */
    public static adminRetryJob({
        jobId,
    }: {
        /**
         * Identifier of the job.
         */
        jobId: string,
    }): CancelablePromise<Job> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/admin/jobs/{job_id}/retry',
            path: {
                'job_id': jobId,
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
     * Read the retention schedules
     * Returns the retention schedule of every entity of this deployment: how long the records are kept, what happens to them afterwards and whether a legal hold is in place. The schedule is the customer policy: the platform does not impose statutory retention values of its own. While a hold is in place the schedule does not run.
     * @returns RetentionSchedule The retention schedules.
     * @throws ApiError
     */
    public static adminGetRetention(): CancelablePromise<Array<RetentionSchedule>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/retention',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Change a retention schedule
     * Changes the schedule of one entity. The change is written to the audit log with the old and the new value. A schedule for an entity the deployment does not have returns 404 `record_not_found`; a retention period that is not a positive number of days returns 422 `validation_error`. A legal hold can only be lifted by an administrator with the compliance role.
     * @returns RetentionSchedule The updated schedule.
     * @throws ApiError
     */
    public static adminUpdateRetention({
        requestBody,
    }: {
        requestBody: RetentionScheduleUpdate,
    }): CancelablePromise<RetentionSchedule> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/admin/retention',
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
     * List the rule packs
     * Lists the rule packs of this deployment: the versioned rule sets of the jurisdictions, with their status, where they came from, how they were verified and how they were signed. A pack is only usable for a payroll run when its status is `verified`. The list is paged; `page` and `page_size` control the window.
     * @returns PaginatedRulePacks A page of rule packs.
     * @throws ApiError
     */
    public static adminListRulePacks({
        page = 1,
        pageSize = 50,
        jurisdiction,
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
         * Only the packs of this jurisdiction.
         */
        jurisdiction?: string,
        /**
         * Only the packs in this state.
         */
        status?: 'draft' | 'verified' | 'deprecated' | 'rejected',
    }): CancelablePromise<PaginatedRulePacks> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/rule-packs',
            query: {
                'page': page,
                'page_size': pageSize,
                'jurisdiction': jurisdiction,
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
     * Read one rule pack
     * Returns one rule pack with its status, its source, the checks of its verification and the signature it carries. A pack that does not exist returns 404 `rule_pack_not_found`. A pack that fails its own load returns 503 `rule_pack_loader_failure` with the reason.
     * @returns RulePack The rule pack.
     * @throws ApiError
     */
    public static adminGetRulePack({
        packId,
    }: {
        /**
         * Identifier of the rule pack.
         */
        packId: string,
    }): CancelablePromise<RulePack> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/admin/rule-packs/{pack_id}',
            path: {
                'pack_id': packId,
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
}
