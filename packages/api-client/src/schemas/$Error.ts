/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Error = {
    description: `The single error object. Mirrors \`contracts/errors.md\` section 1; the two must be changed together.`,
    properties: {
        code: {
            type: 'string',
            description: `Stable machine readable identifier. Snake case. Clients branch on this and never on \`message\`. Renaming a published code is a breaking change.`,
            isRequired: true,
        },
        category: {
            type: 'Enum',
            isRequired: true,
        },
        message: {
            type: 'string',
            description: `Safe to display to a user. No stack traces, no SQL, no hostnames, no record ids that would confirm an object exists. May be reworded at any time, so clients must not parse it.`,
            isRequired: true,
        },
        retryable: {
            type: 'boolean',
            description: `Whether the identical request may succeed later. True only for \`dependency\`, \`rate_limit\` and \`internal\`.`,
            isRequired: true,
        },
        details: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
            isRequired: true,
        },
        request_id: {
            type: 'string',
            description: `Correlates the response with the server log line. Echoed in the \`X-Request-ID\` response header.`,
            isRequired: true,
        },
    },
} as const;
