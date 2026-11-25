/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Health = {
    description: `Deployment health. The deployment holds exactly one customer's data in exactly one Oracle schema; the health probe never reveals the schema name or the DSN.`,
    properties: {
        status: {
            type: 'Enum',
            isRequired: true,
        },
        version: {
            type: 'string',
            description: `Running application version.`,
            isRequired: true,
        },
        checks: {
            type: 'array',
            contains: {
                type: 'HealthCheck',
            },
        },
    },
} as const;
