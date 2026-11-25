/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $OnboardingLaunchResponse = {
    properties: {
        launched: {
            type: 'boolean',
            isRequired: true,
        },
        already_launched: {
            type: 'boolean',
            description: `True when the deployment was already launched. The call was a no op.`,
        },
        job_id: {
            type: 'string',
            description: `Background job that prepares the deployment, when there is one.`,
            isNullable: true,
        },
    },
} as const;
