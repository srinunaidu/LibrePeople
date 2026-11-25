/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ForecastRun } from '../models/ForecastRun';
import type { ForecastRunCreate } from '../models/ForecastRunCreate';
import type { PaginatedForecastRuns } from '../models/PaginatedForecastRuns';
import type { PaginatedScenarios } from '../models/PaginatedScenarios';
import type { ScenarioComparison } from '../models/ScenarioComparison';
import type { ScenarioComparisonRequest } from '../models/ScenarioComparisonRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ForecastingService {
    /**
     * Start a forecast run
     * Starts a forecast of one series of this deployment. The method may be left to the server (`auto`) or overridden explicitly; the method that was actually used is recorded in the result. A series with less history than the method needs is not an error: the run is created, `insufficient_history` is true and the forecast values are omitted. A caller that asks for a minimum history the series cannot satisfy gets 422 `forecast_insufficient_history` with the series, the weeks that are available and the weeks that are required. A series that the deployment does not know returns 422 `validation_error`. A request for a horizon the deployment does not allow returns 422 `validation_error`.
     * @returns ForecastRun The run was created.
     * @throws ApiError
     */
    public static forecastingCreateRun({
        requestBody,
    }: {
        requestBody: ForecastRunCreate,
    }): CancelablePromise<ForecastRun> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/forecasting/runs',
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
     * List the forecast runs
     * Lists the forecast runs of this deployment, newest first. The list is paged; `page` and `page_size` control the window. `metric` and `method` narrow it down. Only runs the caller may see are returned.
     * @returns PaginatedForecastRuns A page of forecast runs.
     * @throws ApiError
     */
    public static forecastingListRuns({
        page = 1,
        pageSize = 50,
        metric,
        method,
        insufficientHistory,
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
         * Only the runs of this metric.
         */
        metric?: string,
        /**
         * Only the runs that used this method.
         */
        method?: string,
        /**
         * Only the runs that were or were not short of history.
         */
        insufficientHistory?: boolean,
    }): CancelablePromise<PaginatedForecastRuns> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/forecasting/runs',
            query: {
                'page': page,
                'page_size': pageSize,
                'metric': metric,
                'method': method,
                'insufficient_history': insufficientHistory,
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
     * Read a forecast run
     * Returns one forecast run with everything needed to judge it:
     * * `method` and `method_version`: the method that was used, after
     * the server resolved `auto`;
     * * `data_window`: the period the model was fitted on and how many
     * observations it saw;
     * * `backtest`: the measured error on a holdout, with `mape`, `mase`
     * and the length of the holdout;
     * * `confidence_band`: the level and the method of the interval the
     * forecast is stated with;
     * * `input_hash`: the hash of the exact input, so the same input
     * gives the same run;
     * * `version`: the version of the run, incremented when the same
     * input is computed again;
     * * `insufficient_history`: true when the series had less history
     * than the method needs. The run is recorded, but it carries no
     * forecast values.
     *
     * A run that does not exist returns 404.
     * @returns ForecastRun The forecast run.
     * @throws ApiError
     */
    public static forecastingGetRun({
        runId,
    }: {
        /**
         * Identifier of the forecast run.
         */
        runId: string,
    }): CancelablePromise<ForecastRun> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/forecasting/runs/{run_id}',
            path: {
                'run_id': runId,
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
     * List the forecast scenarios
     * Lists the scenarios of this deployment. A scenario is a named set of assumptions on top of a base run. The assumptions are part of the scenario and are always returned with it, so a reader can see what was assumed. The list is paged; `page` and `page_size` control the window.
     * @returns PaginatedScenarios A page of scenarios.
     * @throws ApiError
     */
    public static forecastingListScenarios({
        page = 1,
        pageSize = 50,
        baseRunId,
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
         * Only the scenarios on top of this run.
         */
        baseRunId?: string,
    }): CancelablePromise<PaginatedScenarios> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/forecasting/scenarios',
            query: {
                'page': page,
                'page_size': pageSize,
                'base_run_id': baseRunId,
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
     * Compare scenarios
     * Compares two or more scenarios period by period. The response repeats every assumption that was in force, with its origin, next to the numbers: a comparison that does not show its assumptions is not a comparison. The deltas are taken against the first scenario of the request. A scenario that does not exist returns 404.
     * @returns ScenarioComparison The comparison, with the assumptions that produced it.
     * @throws ApiError
     */
    public static forecastingCompareScenarios({
        requestBody,
    }: {
        requestBody: ScenarioComparisonRequest,
    }): CancelablePromise<ScenarioComparison> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/forecasting/scenarios/compare',
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
