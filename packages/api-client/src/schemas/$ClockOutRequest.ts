/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ClockOutRequest = {
    description: `Closes the open working period of the caller, or of \`employee_id\` when an administrator or manager clocks someone out.`,
    properties: {
        employee_id: {
            type: 'string',
        },
        entry_id: {
            type: 'string',
            description: `Explicit entry to close. Defaults to the open entry of the employee.`,
        },
        source: {
            type: 'Enum',
        },
        notes: {
            type: 'string',
            maxLength: 500,
        },
    },
} as const;
