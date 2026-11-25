/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Compare scenarios. Every assumption that is applied is returned in the response so the comparison is reproducible.
 */
export type ScenarioComparisonRequest = {
    scenario_ids: Array<string>;
    /**
     * Periods to compare. Defaults to the shortest scenario horizon.
     */
    horizon?: number;
};

