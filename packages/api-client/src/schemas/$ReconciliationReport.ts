/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ReconciliationReport = {
    description: `A comparison of the computed run against the source data and the previous period, with the variances that need a human look.`,
    properties: {
        run_id: {
            type: 'string',
            isRequired: true,
        },
        generated_at: {
            type: 'string',
            format: 'date-time',
        },
        totals: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
        by_component: {
            type: 'array',
            contains: {
                type: 'dictionary',
                contains: {
                    properties: {
                    },
                },
            },
        },
        variances: {
            type: 'array',
            contains: {
                properties: {
                    code: {
                        type: 'string',
                        description: `Machine readable variance kind, for example \`headcount_delta\`.`,
                        isRequired: true,
                    },
                    entity: {
                        type: 'string',
                        isNullable: true,
                    },
                    amount: {
                        type: 'number',
                    },
                    explanation: {
                        type: 'string',
                    },
                },
            },
        },
        checks: {
            type: 'array',
            contains: {
                properties: {
                    name: {
                        type: 'string',
                        isRequired: true,
                    },
                    passed: {
                        type: 'boolean',
                        isRequired: true,
                    },
                    detail: {
                        type: 'string',
                    },
                },
            },
            isRequired: true,
        },
    },
} as const;
