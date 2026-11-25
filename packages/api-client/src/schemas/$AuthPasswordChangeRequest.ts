/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthPasswordChangeRequest = {
    properties: {
        current_password: {
            type: 'string',
            isRequired: true,
            format: 'password',
        },
        new_password: {
            type: 'string',
            description: `Must satisfy the password policy and must not repeat one of the last N passwords. Failures return 422 \`password_policy_violation\`, \`password_reuse\` or \`password_breached\`.`,
            isRequired: true,
            format: 'password',
        },
    },
} as const;
