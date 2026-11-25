/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConfigGap } from '../models/ConfigGap';
import type { ConfigGapFixRequest } from '../models/ConfigGapFixRequest';
import type { OnboardingLaunchRequest } from '../models/OnboardingLaunchRequest';
import type { OnboardingLaunchResponse } from '../models/OnboardingLaunchResponse';
import type { OnboardingPreset } from '../models/OnboardingPreset';
import type { OnboardingState } from '../models/OnboardingState';
import type { OnboardingStepSubmission } from '../models/OnboardingStepSubmission';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class OnboardingService {
    /**
     * List the configuration gaps
     * Returns the findings of the configuration assistant: everything that is missing, incomplete or inconsistent in the configuration of this deployment. Every finding names the rule that produced it, how serious it is, what it means and what has to change to close it. `severity` narrows the list to the blocking findings or to the others.
     * @returns ConfigGap The configuration gaps.
     * @throws ApiError
     */
    public static onboardingListConfigGaps({
        severity,
        includeApplied = false,
    }: {
        /**
         * Only the findings of this severity.
         */
        severity?: 'blocking' | 'warning' | 'info',
        /**
         * Include the findings that have already been closed.
         */
        includeApplied?: boolean,
    }): CancelablePromise<Array<ConfigGap>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/onboarding/config-gaps',
            query: {
                'severity': severity,
                'include_applied': includeApplied,
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
     * Close one configuration gap
     * Applies the fix of one configuration rule. A rule that can be fixed without further input is closed straight away; a rule that needs values takes them in `parameters` and returns 422 `validation_error` when they are missing or unusable. A rule that does not exist returns 404 `record_not_found`. With `dry_run` the call reports what the fix would change without changing it. A fix that is already applied is a no op.
     * @returns ConfigGap The fix was applied.
     * @throws ApiError
     */
    public static onboardingFixConfigGap({
        ruleId,
        requestBody,
    }: {
        /**
         * Identifier of the configuration rule that produced the gap.
         */
        ruleId: string,
        requestBody?: ConfigGapFixRequest,
    }): CancelablePromise<ConfigGap> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/onboarding/config-gaps/{rule_id}/fix',
            path: {
                'rule_id': ruleId,
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
     * Launch this deployment
     * Launches the deployment once the setup is complete. The call is idempotent: launching a deployment that is already launched is a no op and reports `already_launched`. A deployment with blocking configuration gaps is not launched and returns 409 `invalid_state_transition` with the gaps in `details`. With `dry_run` the call reports what the launch would do without doing it. The call needs an idempotency key, because a client may retry it after a timeout. A missing or malformed idempotency key returns 422 `invalid_idempotency_key`; a request with the same key that is still running returns 409 `request_in_flight`.
     * @returns OnboardingLaunchResponse The deployment was launched, or was already launched.
     * @throws ApiError
     */
    public static onboardingLaunch({
        idempotencyKey,
        requestBody,
    }: {
        /**
         * Caller-generated key (1-200 characters) that makes this mutation safe to retry. Replaying the same key with the same payload returns the original result; replaying it with a different payload is a 409 `idempotency_key_reuse`.
         */
        idempotencyKey: string,
        requestBody?: OnboardingLaunchRequest,
    }): CancelablePromise<OnboardingLaunchResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/onboarding/launch',
            headers: {
                'Idempotency-Key': idempotencyKey,
            },
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
     * List the configuration presets
     * Lists the presets of this deployment: a ready made starting configuration for a kind of business, with the modules to enable, the default roles and the recommended settings. The list is paged; `page` and `page_size` control the window. A preset that is not applicable to this deployment is not listed.
     * @returns OnboardingPreset A page of presets.
     * @throws ApiError
     */
    public static onboardingListPresets({
        page = 1,
        pageSize = 50,
        industry,
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
         * Only the presets of this industry.
         */
        industry?: string,
    }): CancelablePromise<Array<OnboardingPreset>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/onboarding/presets',
            query: {
                'page': page,
                'page_size': pageSize,
                'industry': industry,
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
     * Read one configuration preset
     * Returns one preset with its modules, its default roles and its recommended settings. A preset that does not exist returns 404 `preset_not_found`.
     * @returns OnboardingPreset The preset.
     * @throws ApiError
     */
    public static onboardingGetPreset({
        presetId,
    }: {
        /**
         * Identifier of the preset.
         */
        presetId: string,
    }): CancelablePromise<OnboardingPreset> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/onboarding/presets/{preset_id}',
            path: {
                'preset_id': presetId,
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
     * Read the setup state
     * Returns the state of the setup: the step the deployment is waiting on, the steps that are done, the state of every step and the progress. A deployment that has not started has no current step and zero progress. A deployment that has been launched reports `deployment_ready` and no current step.
     * @returns OnboardingState The setup state.
     * @throws ApiError
     */
    public static onboardingGetState(): CancelablePromise<OnboardingState> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/onboarding/state',
            errors: {
                401: `The access token is missing, malformed, expired or invalid. The body carries the \`unauthenticated\` code. A client may attempt exactly one token refresh before signing out.`,
                403: `The caller is authenticated but not permitted. The body carries \`forbidden\`, \`insufficient_scope\`, \`outside_visibility_scope\` or \`separation_of_duties\`. A record that must not be revealed as existing is reported as 404, not 403.`,
                500: `An unexpected server side failure. The body carries the \`internal\` category and the \`request_id\`; technical detail is logged server side and never returned.`,
                503: `A required dependency (database, object storage, solver, rule pack loader) is unavailable. The body carries the \`dependency\` category and the \`Retry-After\` header states how long to wait. The identical request may succeed later.`,
            },
        });
    }
    /**
     * Submit one setup step
     * Submits one step of the setup and moves the state machine on. The step is named in the path and is one of `company_profile`, `business_type`, `modules`, `import`, `roles`, `review` or `launch`. The payload depends on the step: the profile step takes the company details, the modules step takes the modules to enable, the roles step takes the roles to create. A payload with a field the step does not know returns 422 `validation_error`; a step that cannot be submitted yet, because an earlier step is missing, returns 409 `invalid_state_transition`. Enabling a module whose dependencies are not enabled returns 422 `module_dependency_unmet`. Submitting the same step again is allowed and replaces what that step said.
     * @returns OnboardingState The step was applied and the state was updated.
     * @throws ApiError
     */
    public static onboardingSubmitStep({
        step,
        requestBody,
    }: {
        /**
         * The step to submit.
         */
        step: 'company_profile' | 'business_type' | 'modules' | 'import' | 'roles' | 'review' | 'launch',
        requestBody: OnboardingStepSubmission,
    }): CancelablePromise<OnboardingState> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/onboarding/steps/{step}',
            path: {
                'step': step,
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
}
