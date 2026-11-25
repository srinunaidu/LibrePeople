/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthMfaDisableRequest = {
    properties: {
        recovery_code: {
            type: 'string',
            description: `One unused recovery code. A wrong code returns 422 \`mfa_recovery_code_invalid\` and MFA stays enabled.`,
            isRequired: true,
            minLength: 1,
        },
    },
} as const;
