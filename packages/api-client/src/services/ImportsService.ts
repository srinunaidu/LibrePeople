/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ImportCommitRequest } from '../models/ImportCommitRequest';
import type { ImportDryRunResult } from '../models/ImportDryRunResult';
import type { ImportSummary } from '../models/ImportSummary';
import type { ImportTemplate } from '../models/ImportTemplate';
import type { ImportUpload } from '../models/ImportUpload';
import type { ImportUploadRequest } from '../models/ImportUploadRequest';
import type { Job } from '../models/Job';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ImportsService {
    /**
     * List the expected columns per entity
     * Returns the exact columns each import entity expects, the type of every column, whether it is required and the values it accepts. This is the list a client builds its file from: a column that is not on it is rejected with 422 `import_header_unknown`. The templates are versioned; the version of the template an upload was validated against is reported on the upload.
     * @returns ImportTemplate The templates.
     * @throws ApiError
     */
    public static importsListTemplates({
        entity,
    }: {
        /**
         * Only the template of this entity.
         */
        entity?: string,
    }): CancelablePromise<Array<ImportTemplate>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/imports/templates',
            query: {
                'entity': entity,
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
     * Upload an import file
     * Uploads the file to import and returns the identifier of the upload. The request is `multipart/form-data`: the `file` part carries the bytes, the other parts carry the metadata. The file is only stored at this point: nothing is validated against the entity and nothing is written. An upload that is not used expires. A file that is too large returns 422 `validation_error`.
     * @returns ImportUpload The file was uploaded.
     * @throws ApiError
     */
    public static importsCreateUpload({
        formData,
    }: {
        formData: ImportUploadRequest,
    }): CancelablePromise<ImportUpload> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/imports/uploads',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                429: `The caller exceeded a rate limit. The body carries the \`rate_limit\` category and the \`Retry-After\` header states how long to wait.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read the state of an upload
     * Returns the state of one upload: whether it has been dry run, what the dry run counted, and when the upload expires. An upload that does not exist, or one that has expired, returns 404.
     * @returns ImportUpload The upload.
     * @throws ApiError
     */
    public static importsGetUpload({
        uploadId,
    }: {
        /**
         * Identifier of the upload.
         */
        uploadId: string,
    }): CancelablePromise<ImportUpload> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/imports/uploads/{upload_id}',
            path: {
                'upload_id': uploadId,
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
     * Apply an import
     * Applies the rows of a dry run. The request must present the `confirmation_token` of the dry run together with the `result_hash` it is bound to; a token that does not match returns 422 `import_confirm_token_invalid` and nothing is written. The file is re-validated against the current state of the data, so a row that became invalid in the meantime is rejected rather than applied. The call is idempotent: the same idempotency key with the same payload returns the first result, the same key with another payload returns 409 `idempotency_key_reuse`, and a request with the same key that is still running returns 409 `request_in_flight`. A missing or malformed idempotency key returns 422 `invalid_idempotency_key`. The work is done by a background job; the response carries the job.
     * @returns Job The import was accepted and a job was started.
     * @throws ApiError
     */
    public static importsCommitUpload({
        uploadId,
        idempotencyKey,
        requestBody,
    }: {
        /**
         * Identifier of the upload.
         */
        uploadId: string,
        /**
         * Caller-generated key (1-200 characters) that makes this mutation safe to retry. Replaying the same key with the same payload returns the original result; replaying it with a different payload is a 409 `idempotency_key_reuse`.
         */
        idempotencyKey: string,
        requestBody: ImportCommitRequest,
    }): CancelablePromise<Job> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/imports/uploads/{upload_id}/commit',
            path: {
                'upload_id': uploadId,
            },
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
                429: `The caller exceeded a rate limit. The body carries the \`rate_limit\` category and the \`Retry-After\` header states how long to wait.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Validate an upload without writing anything
     * Validates the uploaded file and reports what would happen, without changing a single row. The response holds the counts of the rows that would be created, updated, left unchanged and rejected, the `result_hash` that covers those counts and the rejected rows, and a downloadable CSV with one line per rejected row. The dry run also hands out a `confirmation_token` that is bound to the result hash: the commit has to present both. A file with headers that are not in the alias table returns 422 `import_header_unknown` with the unknown and the expected headers; a row that fails validation is counted as rejected and listed in the CSV, it does not fail the whole dry run.
     * @returns ImportDryRunResult The counts, the result hash and the row error report.
     * @throws ApiError
     */
    public static importsDryRunUpload({
        uploadId,
    }: {
        /**
         * Identifier of the upload.
         */
        uploadId: string,
    }): CancelablePromise<ImportDryRunResult> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/imports/uploads/{upload_id}/dry-run',
            path: {
                'upload_id': uploadId,
            },
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                404: `The object does not exist, or it is outside the caller's visibility scope. The body carries \`not_found\` or a domain specific variant.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                429: `The caller exceeded a rate limit. The body carries the \`rate_limit\` category and the \`Retry-After\` header states how long to wait.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Read one import
     * Returns the record of one import: the entity, the state, the counts, the result hash of the dry run and, when the import was applied, the job that applied it and who committed it. An import that does not exist returns 404.
     * @returns ImportSummary The import record.
     * @throws ApiError
     */
    public static importsGetImport({
        importId,
    }: {
        /**
         * Identifier of the import.
         */
        importId: string,
    }): CancelablePromise<ImportSummary> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/imports/{import_id}',
            path: {
                'import_id': importId,
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
