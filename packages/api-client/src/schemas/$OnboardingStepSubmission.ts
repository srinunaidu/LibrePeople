/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $OnboardingStepSubmission = {
    description: `The payload of one setup step. The accepted fields depend on the step named in the path; a field the step does not know is rejected with 422 \`validation_error\`.`,
    properties: {
        data: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
        },
        skip: {
            type: 'boolean',
            description: `Mark an optional step as skipped. A required step cannot be skipped.`,
        },
        confirm: {
            type: 'boolean',
            description: `Recompute the downstream steps after this submission.`,
        },
    },
} as const;
