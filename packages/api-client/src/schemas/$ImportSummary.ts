/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImportSummary = {
    description: `The record of one import run.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        entity: {
            type: 'string',
            isRequired: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        counts: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
        result_hash: {
            type: 'string',
            isNullable: true,
        },
        job_id: {
            type: 'string',
            description: `Background job that applied the import.`,
            isNullable: true,
        },
        committed_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        committed_by: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
