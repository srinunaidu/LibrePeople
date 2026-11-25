/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $EmployeeDocument = {
    description: `A document attached to an employee. The file itself is not returned by this endpoint; only its metadata.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        filename: {
            type: 'string',
            isRequired: true,
        },
        content_type: {
            type: 'string',
        },
        size_bytes: {
            type: 'number',
        },
        category: {
            type: 'string',
            description: `Free classification, for example \`contract\` or \`id_proof\`.`,
        },
        checksum: {
            type: 'string',
            description: `SHA-256 of the stored object.`,
        },
        uploaded_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
        uploaded_by: {
            type: 'string',
        },
    },
} as const;
