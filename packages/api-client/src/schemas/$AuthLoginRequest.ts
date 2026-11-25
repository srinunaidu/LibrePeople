/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthLoginRequest = {
    description: `Credentials. The response is identical for an unknown username and a wrong password; the API never enumerates users.`,
    properties: {
        username: {
            type: 'string',
            isRequired: true,
            maxLength: 150,
            minLength: 1,
        },
        password: {
            type: 'string',
            isRequired: true,
            format: 'password',
            maxLength: 256,
            minLength: 1,
        },
    },
} as const;
