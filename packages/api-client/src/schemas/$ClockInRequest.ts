/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ClockInRequest = {
    description: `Starts a working period. When \`employee_id\` is omitted the clock in is attributed to the caller.`,
    properties: {
        employee_id: {
            type: 'string',
            description: `Only an administrator or manager may clock in on behalf of someone else.`,
        },
        location_id: {
            type: 'string',
        },
        source: {
            type: 'Enum',
        },
        device_id: {
            type: 'string',
        },
        notes: {
            type: 'string',
            maxLength: 500,
        },
    },
} as const;
