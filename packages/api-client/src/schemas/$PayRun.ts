/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PayRun = {
    description: `One payroll run. A run moves \`draft\` to \`calculated\` to \`approved\` to \`finalised\`; a finalised run can no longer be edited and returns 409 \`pay_run_already_finalised\`.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        period_id: {
            type: 'string',
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        jurisdiction: {
            type: 'string',
            description: `Jurisdiction whose rule pack applies to this run. The run may not be calculated unless the pack for this jurisdiction is \`verified\`.`,
            isRequired: true,
        },
        rule_pack_id: {
            type: 'string',
            isNullable: true,
        },
        employee_count: {
            type: 'number',
        },
        currency: {
            type: 'string',
        },
        totals: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
        calculated_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        approved_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        approved_by: {
            type: 'string',
            isNullable: true,
        },
        finalised_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
    },
} as const;
