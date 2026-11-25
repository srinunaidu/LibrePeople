/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthMfaConfirmRequest = {
    properties: {
        code: {
            type: 'string',
            description: `The current TOTP code. A wrong code returns 422 \`mfa_invalid_code\`.`,
            isRequired: true,
            maxLength: 10,
            minLength: 6,
        },
    },
} as const;
