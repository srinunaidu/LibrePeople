/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PayProfile = {
    description: `A named set of pay components used by pay runs.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        currency: {
            type: 'string',
            description: `ISO 4217 currency code of the profile.`,
        },
        pay_frequency: {
            type: 'Enum',
        },
        component_ids: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
        active: {
            type: 'boolean',
        },
    },
} as const;
