/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * How the candidate roster was produced. Recorded so a planner can judge the result and reproduce it later.
 */
export type SolverMetadata = {
    /**
     * Solver engine and version that produced the result.
     */
    solver: string;
    status: SolverMetadata.status;
    time_limit_seconds?: number;
    solve_time_ms?: number;
    /**
     * Value of the weighted objective the solver minimised.
     */
    objective_value?: number;
    evaluated_nodes?: number;
    /**
     * Hash of the solver input, so the same input gives the same result.
     */
    input_hash?: string;
};
export namespace SolverMetadata {
    export enum status {
        OPTIMAL = 'optimal',
        FEASIBLE = 'feasible',
        TIMEOUT = 'timeout',
        INFEASIBLE = 'infeasible',
    }
}

