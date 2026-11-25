/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RetentionSchedule = {
    description: `How long the records of one entity are kept, and what happens to them afterwards. The schedule is the customer policy; the platform does not impose statutory retention values.`,
    properties: {
        entity: {
            type: 'string',
            isRequired: true,
        },
        retention_days: {
            type: 'number',
            isRequired: true,
            minimum: 1,
        },
        action: {
            type: 'Enum',
            isRequired: true,
        },
        legal_hold: {
            type: 'boolean',
            description: `While a hold is in place the schedule does not run, whatever it says.`,
        },
        updated_at: {
            type: 'string',
            format: 'date-time',
        },
        updated_by: {
            type: 'string',
        },
        last_run_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
    },
} as const;
