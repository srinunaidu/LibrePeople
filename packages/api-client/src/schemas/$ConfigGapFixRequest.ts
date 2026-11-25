/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ConfigGapFixRequest = {
    description: `The request that resolves one configuration gap.`,
    properties: {
        parameters: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
        dry_run: {
            type: 'boolean',
            description: `Report what the fix would do without applying it.`,
        },
    },
} as const;
