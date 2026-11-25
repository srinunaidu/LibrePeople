/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthUser = {
    description: `A user account of this deployment.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        username: {
            type: 'string',
            isRequired: true,
        },
        email: {
            type: 'string',
            format: 'email',
        },
        role: {
            type: 'string',
            description: `Role held by the account.`,
            isRequired: true,
        },
        is_active: {
            type: 'boolean',
            description: `A disabled account cannot authenticate.`,
            isRequired: true,
        },
        must_change_password: {
            type: 'boolean',
        },
        mfa_enabled: {
            type: 'boolean',
        },
        created_at: {
            type: 'string',
            format: 'date-time',
        },
        last_login_at: {
            type: 'string',
            format: 'date-time',
        },
    },
} as const;
