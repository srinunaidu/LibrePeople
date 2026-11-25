/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthRefreshResponse = {
    properties: {
        access_token: {
            type: 'string',
            isRequired: true,
        },
        token_type: {
            type: 'Enum',
            isRequired: true,
        },
        expires_in: {
            type: 'number',
            isRequired: true,
            minimum: 1,
        },
        refresh_token: {
            type: 'string',
            description: `The rotated refresh token. The presented token is invalidated. If an already rotated token is presented again the whole token family is revoked and the response is 401 \`refresh_token_reused\`.`,
            isRequired: true,
        },
    },
} as const;
