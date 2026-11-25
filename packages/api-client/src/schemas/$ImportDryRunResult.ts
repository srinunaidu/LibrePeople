/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImportDryRunResult = {
    description: `The outcome of validating a file without writing anything. The \`result_hash\` covers the counts and the rejected rows; the commit must present a confirmation token that is bound to it.`,
    properties: {
        upload_id: {
            type: 'string',
            isRequired: true,
        },
        counts: {
            properties: {
                created: {
                    type: 'number',
                    isRequired: true,
                },
                updated: {
                    type: 'number',
                    isRequired: true,
                },
                unchanged: {
                    type: 'number',
                    isRequired: true,
                },
                rejected: {
                    type: 'number',
                    isRequired: true,
                },
                total: {
                    type: 'number',
                    isRequired: true,
                },
            },
            isRequired: true,
        },
        result_hash: {
            type: 'string',
            description: `Hash of the dry run outcome. The commit request must quote it and the confirmation token must be bound to it.`,
            isRequired: true,
        },
        confirmation_token: {
            type: 'string',
            description: `Opaque token to present at commit time. It is bound to the result hash; a token that does not match returns 422 \`import_confirm_token_invalid\`.`,
        },
        errors: {
            type: 'array',
            contains: {
                properties: {
                    row: {
                        type: 'number',
                        isRequired: true,
                        minimum: 1,
                    },
                    field: {
                        type: 'string',
                        isNullable: true,
                    },
                    reason: {
                        type: 'string',
                        isRequired: true,
                    },
                    code: {
                        type: 'string',
                        description: `A code from the shared code list, for example \`import_row_invalid\`.`,
                    },
                },
            },
        },
        errors_csv: {
            description: `The downloadable row error report.`,
            properties: {
                filename: {
                    type: 'string',
                    isRequired: true,
                },
                download_url: {
                    type: 'string',
                    description: `Short lived URL of the CSV with one row per rejected line.`,
                    isRequired: true,
                },
                expires_at: {
                    type: 'string',
                    format: 'date-time',
                },
            },
        },
        expires_at: {
            type: 'string',
            description: `After this moment the confirmation token is no longer valid.`,
            format: 'date-time',
        },
    },
} as const;
