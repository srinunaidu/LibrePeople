/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $UnfilledSlot = {
    description: `A requirement the solver could not satisfy, and why. \`causes\` is machine readable so a client can explain the gap without parsing prose.`,
    properties: {
        shift_template_id: {
            type: 'string',
            isRequired: true,
        },
        work_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        required_headcount: {
            type: 'number',
            isRequired: true,
        },
        filled: {
            type: 'number',
            isRequired: true,
        },
        causes: {
            type: 'array',
            contains: {
                type: 'string',
            },
            isRequired: true,
        },
    },
} as const;
