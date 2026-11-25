/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthUserCreateRequest = {
    properties: {
        username: {
            type: 'string',
            isRequired: true,
            maxLength: 150,
            minLength: 3,
        },
        email: {
            type: 'string',
            isRequired: true,
            format: 'email',
        },
        password: {
            type: 'string',
            description: `Must satisfy the deployment password policy. A rejected password returns 422 \`password_policy_violation\`; a password on the local breached list returns 422 \`password_breached\`.`,
            isRequired: true,
            format: 'password',
        },
        role: {
            type: 'string',
            description: `Role to grant. Only an administrator may call this endpoint.`,
            isRequired: true,
        },
        send_invite: {
            type: 'boolean',
            description: `When true the account is created with \`must_change_password\` set and no password is delivered to the user.`,
        },
    },
} as const;
