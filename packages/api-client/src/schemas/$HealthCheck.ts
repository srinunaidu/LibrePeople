/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $HealthCheck = {
    properties: {
        name: {
            type: 'string',
            description: `Name of the dependency that was probed.`,
            isRequired: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        detail: {
            type: 'string',
            description: `Safe to display detail. No DSN, no host, no path.`,
        },
    },
} as const;
