/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $EntryCorrectionRequest = {
    description: `A manual correction of a recorded working period. A correction is never applied directly: it is recorded as a pending request and the entry keeps its original value until a manager approves it.`,
    properties: {
        work_date: {
            type: 'string',
            format: 'date',
        },
        clock_in: {
            type: 'string',
            format: 'date-time',
        },
        clock_out: {
            type: 'string',
            format: 'date-time',
        },
        minutes: {
            type: 'number',
            description: `Total worked minutes after correction.`,
        },
        reason: {
            type: 'string',
            description: `Why the correction is needed. Stored on the audit trail.`,
            isRequired: true,
            maxLength: 500,
            minLength: 5,
        },
    },
} as const;
