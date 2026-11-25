/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $LeaveType = {
    description: `A leave type configured for this deployment.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        code: {
            type: 'string',
            description: `Stable code used in imports and exports.`,
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        unit: {
            type: 'Enum',
            isRequired: true,
        },
        accrual_method: {
            type: 'Enum',
        },
        requires_approval: {
            type: 'boolean',
        },
        max_consecutive_days: {
            type: 'number',
            isNullable: true,
        },
        active: {
            type: 'boolean',
        },
    },
} as const;
