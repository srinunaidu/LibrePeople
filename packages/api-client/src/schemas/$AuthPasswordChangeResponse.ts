/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthPasswordChangeResponse = {
    properties: {
        changed: {
            type: 'boolean',
            isRequired: true,
        },
        sessions_revoked: {
            type: 'boolean',
            description: `True when all other sessions of the account were revoked.`,
        },
    },
} as const;
