/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuditVerification = {
    description: `The result of walking the audit chain. When the chain is broken the first broken link is reported, with the index it was found at.`,
    properties: {
        verified: {
            type: 'boolean',
            isRequired: true,
        },
        checked_entries: {
            type: 'number',
            isRequired: true,
        },
        first_broken: {
            description: `Where the chain stopped holding.`,
            properties: {
                id: {
                    type: 'string',
                    isNullable: true,
                },
                index: {
                    type: 'number',
                    isRequired: true,
                },
                reason: {
                    type: 'string',
                    description: `Machine readable reason, for example \`hash_mismatch\` or \`missing_predecessor\`.`,
                    isRequired: true,
                },
            },
            isNullable: true,
        },
        verified_at: {
            type: 'string',
            format: 'date-time',
        },
    },
} as const;
