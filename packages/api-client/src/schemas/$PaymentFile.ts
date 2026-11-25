/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PaymentFile = {
    description: `The exported payment file of a finalised run. The file itself is fetched from the download URL, never inlined.`,
    properties: {
        run_id: {
            type: 'string',
            isRequired: true,
        },
        format: {
            type: 'Enum',
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
        sha256: {
            type: 'string',
        },
        generated_at: {
            type: 'string',
            format: 'date-time',
        },
        download_url: {
            type: 'string',
            description: `Short lived URL. The file is served by the object storage backend.`,
        },
    },
} as const;
