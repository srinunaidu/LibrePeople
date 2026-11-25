/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ScenarioComparison = {
    description: `The side by side result of a scenario comparison.`,
    properties: {
        scenarios: {
            type: 'array',
            contains: {
                type: 'ForecastScenario',
            },
            isRequired: true,
        },
        assumptions: {
            type: 'array',
            contains: {
                type: 'dictionary',
                contains: {
                    properties: {
                    },
                },
            },
            isRequired: true,
        },
        series: {
            type: 'array',
            contains: {
                type: 'dictionary',
                contains: {
                    properties: {
                    },
                },
            },
        },
        deltas: {
            type: 'array',
            contains: {
                type: 'dictionary',
                contains: {
                    properties: {
                    },
                },
            },
        },
    },
} as const;
