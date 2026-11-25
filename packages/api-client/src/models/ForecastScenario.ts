/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A named set of assumptions on top of a forecast run. The assumptions are always shown, never applied silently.
 */
export type ForecastScenario = {
    id: string;
    name: string;
    description?: string;
    base_run_id?: string | null;
    assumptions: Array<{
        /**
         * Machine readable assumption key, for example `absence_rate_delta`.
         */
        key: string;
        value: number;
        unit?: string;
        /**
         * Why the assumption was made.
         */
        note?: string;
    }>;
    created_at?: string;
};

