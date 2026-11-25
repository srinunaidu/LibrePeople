/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Coverage of the demand for a location and a period, with the gaps that remain.
 */
export type CoverageResponse = {
    location_id: string;
    start_date: string;
    end_date: string;
    demand_total: number;
    covered: number;
    coverage_ratio?: number;
    gaps?: Array<{
        work_date: string;
        shift_template_id: string;
        shortfall: number;
    }>;
};

