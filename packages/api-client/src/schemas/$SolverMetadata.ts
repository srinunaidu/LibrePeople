/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $SolverMetadata = {
    description: `How the candidate roster was produced. Recorded so a planner can judge the result and reproduce it later.`,
    properties: {
        solver: {
            type: 'string',
            description: `Solver engine and version that produced the result.`,
            isRequired: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        time_limit_seconds: {
            type: 'number',
        },
        solve_time_ms: {
            type: 'number',
        },
        objective_value: {
            type: 'number',
            description: `Value of the weighted objective the solver minimised.`,
        },
        evaluated_nodes: {
            type: 'number',
        },
        input_hash: {
            type: 'string',
            description: `Hash of the solver input, so the same input gives the same result.`,
        },
    },
} as const;
