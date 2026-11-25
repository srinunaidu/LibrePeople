/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Calculation input. `dry_run` defaults to true: a dry run computes everything and writes nothing.
 */
export type PayRunCalculateRequest = {
    /**
     * True computes the run without persisting results. False persists the calculation and moves the run to `calculated`.
     */
    dry_run?: boolean;
    /**
     * Restrict the calculation to these employees.
     */
    employee_ids?: Array<string>;
    /**
     * Include employees with a zero result.
     */
    include_zero?: boolean;
};

