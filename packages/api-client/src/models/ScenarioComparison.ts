/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ForecastScenario } from './ForecastScenario';
/**
 * The side by side result of a scenario comparison.
 */
export type ScenarioComparison = {
    scenarios: Array<ForecastScenario>;
    /**
     * The assumptions that were in force, with their origin.
     */
    assumptions: Array<Record<string, any>>;
    /**
     * One row per period with the value of every scenario.
     */
    series?: Array<Record<string, any>>;
    /**
     * Difference of every scenario against the first one.
     */
    deltas?: Array<Record<string, any>>;
};

