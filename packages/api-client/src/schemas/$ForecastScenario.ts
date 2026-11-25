/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ForecastScenario = {
    description: `A named set of assumptions on top of a forecast run. The assumptions are always shown, never applied silently.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        description: {
            type: 'string',
        },
        base_run_id: {
            type: 'string',
            isNullable: true,
        },
        assumptions: {
            type: 'array',
            contains: {
                properties: {
                    key: {
                        type: 'string',
                        description: `Machine readable assumption key, for example \`absence_rate_delta\`.`,
                        isRequired: true,
                    },
                    value: {
                        type: 'number',
                        isRequired: true,
                    },
                    unit: {
                        type: 'string',
                    },
                    note: {
                        type: 'string',
                        description: `Why the assumption was made.`,
                    },
                },
            },
            isRequired: true,
        },
        created_at: {
            type: 'string',
            format: 'date-time',
        },
    },
} as const;
