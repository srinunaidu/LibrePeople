/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthLoginResponse = {
    properties: {
        access_token: {
            type: 'string',
            description: `JWT access token. Send as \`Authorization: Bearer <token>\`.`,
            isRequired: true,
        },
        token_type: {
            type: 'Enum',
            isRequired: true,
        },
        expires_in: {
            type: 'number',
            description: `Access token lifetime in seconds.`,
            isRequired: true,
            minimum: 1,
        },
        role: {
            type: 'string',
            description: `Role granted to the account.`,
            isRequired: true,
        },
        must_change_password: {
            type: 'boolean',
            description: `True when the account still has to set its own password. The token is valid but privileged calls return 401 \`password_change_required\`.`,
            isRequired: true,
        },
        refresh_token: {
            type: 'string',
            description: `Refresh token, issued when refresh token rotation is enabled. Presented to \`POST /auth/refresh\`, never to any other endpoint.`,
        },
    },
} as const;
