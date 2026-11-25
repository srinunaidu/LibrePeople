/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthLogoutResponse = {
    properties: {
        revoked: {
            type: 'boolean',
            description: `True when the access token and any supplied refresh token were revoked.`,
            isRequired: true,
        },
    },
} as const;
