/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthRecoveryCodesResponse = {
    description: `Fresh recovery codes. The plaintext is returned exactly once, at generation time, and is not recoverable afterwards.`,
    properties: {
        codes: {
            type: 'array',
            contains: {
                type: 'string',
            },
            isRequired: true,
        },
        generated_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
    },
} as const;
