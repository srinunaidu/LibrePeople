/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PayRunCalculateRequest = {
    description: `Calculation input. \`dry_run\` defaults to true: a dry run computes everything and writes nothing.`,
    properties: {
        dry_run: {
            type: 'boolean',
            description: `True computes the run without persisting results. False persists the calculation and moves the run to \`calculated\`.`,
        },
        employee_ids: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
        include_zero: {
            type: 'boolean',
            description: `Include employees with a zero result.`,
        },
    },
} as const;
