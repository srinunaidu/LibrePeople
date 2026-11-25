/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $OnboardingState = {
    description: `The resumable setup state machine of this deployment. Every step can be submitted again; the state records what is done and what is next.`,
    properties: {
        current_step: {
            type: 'Enum',
            isRequired: true,
            isNullable: true,
        },
        completed_steps: {
            type: 'array',
            contains: {
                type: 'Enum',
            },
            isRequired: true,
        },
        steps: {
            type: 'array',
            contains: {
                properties: {
                    id: {
                        type: 'string',
                        isRequired: true,
                    },
                    title: {
                        type: 'string',
                    },
                    status: {
                        type: 'Enum',
                        isRequired: true,
                    },
                    required: {
                        type: 'boolean',
                    },
                    completed_at: {
                        type: 'string',
                        isNullable: true,
                        format: 'date-time',
                    },
                },
            },
        },
        progress: {
            properties: {
                completed: {
                    type: 'number',
                    isRequired: true,
                },
                total: {
                    type: 'number',
                    isRequired: true,
                },
                percent: {
                    type: 'number',
                    maximum: 100,
                },
            },
            isRequired: true,
        },
        started_at: {
            type: 'string',
            format: 'date-time',
        },
        updated_at: {
            type: 'string',
            format: 'date-time',
        },
        deployment_ready: {
            type: 'boolean',
            description: `True when the deployment has been launched and is ready for use.`,
        },
    },
} as const;
