/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Payslip = {
    description: `The payslip of one employee for one run. Amounts are in the run currency and are only final once the run is finalised.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        run_id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        period_id: {
            type: 'string',
        },
        currency: {
            type: 'string',
        },
        gross: {
            type: 'number',
        },
        deductions: {
            type: 'number',
        },
        net: {
            type: 'number',
        },
        lines: {
            type: 'array',
            contains: {
                properties: {
                    code: {
                        type: 'string',
                        isRequired: true,
                    },
                    name: {
                        type: 'string',
                        isRequired: true,
                    },
                    amount: {
                        type: 'number',
                        isRequired: true,
                    },
                    category: {
                        type: 'string',
                    },
                },
            },
        },
        issued_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
    },
} as const;
