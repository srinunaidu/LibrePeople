/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImportCommitRequest = {
    description: `The confirmation of an import. The token and the result hash must match the dry run they refer to.`,
    properties: {
        confirmation_token: {
            type: 'string',
            description: `The token returned by the dry run.`,
            isRequired: true,
        },
        result_hash: {
            type: 'string',
            description: `The result hash returned by the dry run.`,
            isRequired: true,
        },
        comment: {
            type: 'string',
            description: `Optional note stored with the import record.`,
            maxLength: 500,
        },
    },
} as const;
