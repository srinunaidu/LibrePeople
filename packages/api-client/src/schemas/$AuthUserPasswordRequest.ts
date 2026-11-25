/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthUserPasswordRequest = {
    properties: {
        password: {
            type: 'string',
            description: `The administrator sets the initial password. The account is marked \`must_change_password\` and cannot act until it is changed.`,
            isRequired: true,
            format: 'password',
        },
    },
} as const;
