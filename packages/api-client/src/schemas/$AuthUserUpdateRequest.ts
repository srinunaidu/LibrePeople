/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuthUserUpdateRequest = {
    description: `Partial update. \`role\` changes are audited; setting \`is_active\` to false revokes every live session of that account.`,
    properties: {
        email: {
            type: 'string',
            format: 'email',
        },
        role: {
            type: 'string',
        },
        is_active: {
            type: 'boolean',
        },
    },
} as const;
