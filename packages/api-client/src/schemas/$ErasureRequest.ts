/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ErasureRequest = {
    description: `A request to erase the personal data of one subject. The request is handled by a background job and never removes rows that are under a legal hold.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isNullable: true,
        },
        subject_type: {
            type: 'Enum',
            isRequired: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        legal_basis: {
            type: 'string',
            description: `The basis the erasure was made under.`,
            isNullable: true,
        },
        requested_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
        completed_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        job_id: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
