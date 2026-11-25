/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ErasureRequestCreate = {
    properties: {
        employee_id: {
            type: 'string',
            description: `Required when \`subject_type\` is \`employee\`.`,
        },
        subject_type: {
            type: 'Enum',
            isRequired: true,
        },
        legal_basis: {
            type: 'string',
            maxLength: 500,
        },
        reason: {
            type: 'string',
            maxLength: 500,
        },
    },
} as const;
