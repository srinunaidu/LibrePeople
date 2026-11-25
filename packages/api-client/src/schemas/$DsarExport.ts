/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $DsarExport = {
    description: `A data subject access export: the whole record the platform holds about one subject, in one file.`,
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
        format: {
            type: 'Enum',
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
        download_url: {
            type: 'string',
            description: `Short lived URL of the export file.`,
            isNullable: true,
        },
        expires_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        file_sha256: {
            type: 'string',
            isNullable: true,
        },
        job_id: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
