/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthLogoutRequest = {
    properties: {
        refresh_token: {
            type: 'string',
            description: `Optional refresh token to revoke. Without it only the presented access token is invalidated.`,
        },
    },
} as const;
