/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthMfaEnrollResponse = {
    description: `TOTP enrolment material. The shared secret is returned exactly once, at enrolment time. It is never shown again and never included in any later response.`,
    properties: {
        secret: {
            type: 'string',
            description: `Base32 TOTP shared secret. Shown once.`,
            isRequired: true,
        },
        otpauth_uri: {
            type: 'string',
            description: `The \`otpauth://\` URI to scan into an authenticator app.`,
            isRequired: true,
        },
        digits: {
            type: 'number',
        },
        period: {
            type: 'number',
            description: `TOTP time step in seconds.`,
        },
        algorithm: {
            type: 'string',
        },
    },
} as const;
