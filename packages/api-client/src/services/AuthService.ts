/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AuthLoginRequest } from '../models/AuthLoginRequest';
import type { AuthLoginResponse } from '../models/AuthLoginResponse';
import type { AuthLogoutRequest } from '../models/AuthLogoutRequest';
import type { AuthLogoutResponse } from '../models/AuthLogoutResponse';
import type { AuthMfaConfirmRequest } from '../models/AuthMfaConfirmRequest';
import type { AuthMfaDisableRequest } from '../models/AuthMfaDisableRequest';
import type { AuthMfaEnrollResponse } from '../models/AuthMfaEnrollResponse';
import type { AuthPasswordChangeRequest } from '../models/AuthPasswordChangeRequest';
import type { AuthPasswordChangeResponse } from '../models/AuthPasswordChangeResponse';
import type { AuthRecoveryCodesResponse } from '../models/AuthRecoveryCodesResponse';
import type { AuthRefreshRequest } from '../models/AuthRefreshRequest';
import type { AuthRefreshResponse } from '../models/AuthRefreshResponse';
import type { AuthUser } from '../models/AuthUser';
import type { AuthUserCreateRequest } from '../models/AuthUserCreateRequest';
import type { AuthUserPasswordRequest } from '../models/AuthUserPasswordRequest';
import type { AuthUserUpdateRequest } from '../models/AuthUserUpdateRequest';
import type { PaginatedUsers } from '../models/PaginatedUsers';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Exchange credentials for an access token
     * Exchanges a username and a password for an access token. The response is identical for an unknown username and a wrong password, so the endpoint never confirms whether an account exists. Repeated failures from one address are throttled: 429 `login_attempts_exceeded` carries the `Retry-After` header. An account that is disabled returns 401 `account_disabled`; an account locked by the lockout policy returns 401 `account_locked` with `retry_after_seconds` in `details`.
     * @returns AuthLoginResponse The credentials were accepted. When `must_change_password` is true the token is valid but every call other than the password change returns 401 `password_change_required`.
     * @throws ApiError
     */
    public static authLogin({
        requestBody,
    }: {
        requestBody: AuthLoginRequest,
    }): CancelablePromise<AuthLoginResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/login',
            body: requestBody,
            mediaType: 'application/json',
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
     * Revoke the current session
     * Revokes the presented access token and, when a refresh token is supplied, the refresh token family behind it. The call is idempotent: revoking an already revoked token still returns 200.
     * @returns AuthLogoutResponse The session was revoked.
     * @throws ApiError
     */
    public static authLogout({
        requestBody,
    }: {
        requestBody?: AuthLogoutRequest,
    }): CancelablePromise<AuthLogoutResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/logout',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Describe the authenticated caller
     * Returns the account, the role and the effective permissions of the caller. A caller whose account still has to change its password gets 401 `password_change_required` instead of the account.
     * @returns AuthUser The account of the caller.
     * @throws ApiError
     */
    public static authGetMe(): CancelablePromise<AuthUser> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/me',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Confirm TOTP enrolment
     * Confirms the enrolment by presenting a code from the authenticator app. A wrong or expired code returns 422 `mfa_invalid_code` and the second factor stays inactive. The call also issues recovery codes, returned once.
     * @returns AuthRecoveryCodesResponse The second factor is active. The recovery codes in the response are shown once.
     * @throws ApiError
     */
    public static authConfirmMfa({
        requestBody,
    }: {
        requestBody: AuthMfaConfirmRequest,
    }): CancelablePromise<AuthRecoveryCodesResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/mfa/confirm',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Turn the second factor off
     * Turns the second factor off for the caller. A recovery code must be presented. A wrong code returns 422 `mfa_recovery_code_invalid` and the second factor stays on. Every other session of the account is revoked.
     * @returns AuthLogoutResponse The second factor is off.
     * @throws ApiError
     */
    public static authDisableMfa({
        requestBody,
    }: {
        requestBody: AuthMfaDisableRequest,
    }): CancelablePromise<AuthLogoutResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/mfa/disable',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Start TOTP enrolment
     * Starts the enrolment of a time based one time password. The response carries the shared secret and the `otpauth://` URI. The secret is returned exactly once, here: it is never shown again and never included in any later response. The second factor is not active until `POST /auth/mfa/confirm` succeeds.
     * @returns AuthMfaEnrollResponse The enrolment material. Shown once.
     * @throws ApiError
     */
    public static authEnrollMfa(): CancelablePromise<AuthMfaEnrollResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/mfa/enroll',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                409: `The request conflicts with the current state of the resource: a duplicate natural key, an illegal state transition, a reused idempotency key, or a concurrent modification. The body carries the \`conflict\` or \`concurrency\` category.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Change the password of the caller
     * Changes the password of the authenticated caller. The current password must be supplied. A new password that breaks the policy returns 422 `password_policy_violation` with the list of violations in `details`; a password that repeats one of the last N returns 422 `password_reuse`; a password on the local breached password list returns 422 `password_breached`. Changing the password revokes the other sessions of the account.
     * @returns AuthPasswordChangeResponse The password was changed.
     * @throws ApiError
     */
    public static authChangePassword({
        requestBody,
    }: {
        requestBody: AuthPasswordChangeRequest,
    }): CancelablePromise<AuthPasswordChangeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Regenerate the recovery codes of the caller
     * Replaces the recovery codes of the caller with a fresh set. The plaintext codes are returned exactly once, in this response, and are not recoverable afterwards. The codes that were replaced stop working immediately.
     * @returns AuthRecoveryCodesResponse The new recovery codes. Shown once.
     * @throws ApiError
     */
    public static authRegenerateRecoveryCodes(): CancelablePromise<AuthRecoveryCodesResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/recovery-codes',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Rotate a refresh token and issue a new access token
     * Exchanges a refresh token for a new access token and a new refresh token. The presented refresh token is invalidated by the rotation. Presenting a token that was already rotated is treated as a stolen token: the whole token family is revoked and the response is 401 `refresh_token_reused`. An unknown, expired or revoked token returns 401 `refresh_token_invalid`. A client may attempt this exactly once after a 401 before it signs the user out.
     * @returns AuthRefreshResponse A new access token and a rotated refresh token.
     * @throws ApiError
     */
    public static authRefresh({
        requestBody,
    }: {
        requestBody: AuthRefreshRequest,
    }): CancelablePromise<AuthRefreshResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                422: `The request failed validation. The body carries the \`validation\` category; \`details\` holds the field level context for the specific code (for example \`password_policy_violation\` carries \`{violations: [...]}\`).`,
                429: `The caller exceeded a rate limit. The body carries the \`rate_limit\` category and the \`Retry-After\` header states how long to wait.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * List the user accounts of this deployment
     * Lists the user accounts of this deployment. Administrators only. The list is paged; `page` and `page_size` control the window. The route already exists in the application; the paged envelope is the shape the contract promises.
     * @returns PaginatedUsers A page of user accounts.
     * @throws ApiError
     */
    public static authListUsers({
        page = 1,
        pageSize = 50,
        role,
        isActive,
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
         * Only accounts with this role.
         */
        role?: string,
        /**
         * Only active or only deactivated accounts.
         */
        isActive?: boolean,
        /**
         * Case insensitive match on the username and the email address.
         */
        search?: string,
    }): CancelablePromise<PaginatedUsers> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/users',
            query: {
                'page': page,
                'page_size': pageSize,
                'role': role,
                'is_active': isActive,
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
     * Create a user account
     * Creates a user account with a role. Administrators only. The password must satisfy the deployment policy; a rejected password returns 422 `password_policy_violation` and a breached password returns 422 `password_breached`. With `send_invite` the account is created with `must_change_password` set and no password is handed out. The route already exists in the application; the payload of this contract is the shape it promises.
     * @returns AuthUser The account was created.
     * @throws ApiError
     */
    public static authCreateUser({
        requestBody,
    }: {
        requestBody: AuthUserCreateRequest,
    }): CancelablePromise<AuthUser> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/users',
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
     * Change a user account
     * Updates the role, the email address or the active state of an account. Administrators only. Deactivating an account revokes every live session of that account. The change is written to the audit log.
     * @returns AuthUser The updated account.
     * @throws ApiError
     */
    public static authUpdateUser({
        userId,
        requestBody,
    }: {
        /**
         * Identifier of the account.
         */
        userId: string,
        requestBody: AuthUserUpdateRequest,
    }): CancelablePromise<AuthUser> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/auth/users/{user_id}',
            path: {
                'user_id': userId,
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
     * Set the password of a user account
     * Sets the password of an account from the administration side. The account is marked `must_change_password` and cannot act until the user has changed it. Administrators only. The password must satisfy the deployment policy.
     * @returns AuthUser The password was set.
     * @throws ApiError
     */
    public static authSetUserPassword({
        userId,
        requestBody,
    }: {
        /**
         * Identifier of the account.
         */
        userId: string,
        requestBody: AuthUserPasswordRequest,
    }): CancelablePromise<AuthUser> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/users/{user_id}/password',
            path: {
                'user_id': userId,
            },
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
}
