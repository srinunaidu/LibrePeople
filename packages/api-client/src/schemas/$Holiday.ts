/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Holiday = {
    description: `A non working day for one location. The list is maintained by the customer; statutory dates are never hard coded by the platform.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        location_id: {
            type: 'string',
            isRequired: true,
        },
        jurisdiction: {
            type: 'string',
            description: `Optional jurisdiction label, used to match a rule pack.`,
            isNullable: true,
        },
        is_public: {
            type: 'boolean',
        },
    },
} as const;
