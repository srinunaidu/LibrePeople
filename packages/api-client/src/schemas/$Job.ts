/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Job = {
    description: `A background job. Jobs report failures with the same code vocabulary as the HTTP API (see \`contracts/errors.md\` section 6).`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        type: {
            type: 'string',
            description: `Job type, for example \`import_commit\` or \`payroll_calculate\`.`,
            isRequired: true,
        },
        state: {
            type: 'JobStatus',
            isRequired: true,
        },
        attempts: {
            type: 'number',
            isRequired: true,
        },
        max_attempts: {
            type: 'number',
            isRequired: true,
            minimum: 1,
        },
        created_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
        updated_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
        started_at: {
            type: 'string',
            format: 'date-time',
        },
        last_error_at: {
            type: 'string',
            format: 'date-time',
        },
        error_code: {
            type: 'string',
            description: `A code from the shared code list in \`contracts/errors.md\`.`,
        },
        error_message: {
            type: 'string',
            description: `Safe to display. Never contains internals.`,
        },
        payload: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
        result: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
    },
} as const;
