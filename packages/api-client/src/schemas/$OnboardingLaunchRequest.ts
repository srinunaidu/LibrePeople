/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $OnboardingLaunchRequest = {
    description: `The launch of this deployment. The call is idempotent: launching an already launched deployment returns the same result.`,
    properties: {
        confirm: {
            type: 'boolean',
            description: `Must be true. Guards against an accidental launch.`,
        },
        dry_run: {
            type: 'boolean',
            description: `Report what the launch would do without doing it.`,
        },
    },
} as const;
