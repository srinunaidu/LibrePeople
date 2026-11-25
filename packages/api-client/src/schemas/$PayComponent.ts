/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PayComponent = {
    description: `One element of a pay profile.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        code: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        category: {
            type: 'Enum',
            isRequired: true,
        },
        taxable: {
            type: 'boolean',
        },
        calculation_type: {
            type: 'Enum',
        },
        calculation_value: {
            type: 'string',
            description: `Opaque calculation expression. The customer owns the formula; the platform does not publish statutory values.`,
        },
        sequence: {
            type: 'number',
            description: `Order in which the component is calculated.`,
        },
    },
} as const;
