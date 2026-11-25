/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ScenarioComparisonRequest = {
    description: `Compare scenarios. Every assumption that is applied is returned in the response so the comparison is reproducible.`,
    properties: {
        scenario_ids: {
            type: 'array',
            contains: {
                type: 'string',
            },
            isRequired: true,
        },
        horizon: {
            type: 'number',
            description: `Periods to compare. Defaults to the shortest scenario horizon.`,
            minimum: 1,
        },
    },
} as const;
