/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $OnboardingPreset = {
    description: `A starting configuration for a kind of business: the modules to enable, the default roles and the recommended settings.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        description: {
            type: 'string',
        },
        industry: {
            type: 'string',
            isNullable: true,
        },
        modules: {
            type: 'array',
            contains: {
                type: 'string',
            },
            isRequired: true,
        },
        default_roles: {
            type: 'array',
            contains: {
                type: 'dictionary',
                contains: {
                    properties: {
                    },
                },
            },
        },
        recommended_settings: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
    },
} as const;
