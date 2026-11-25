/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $SwapRequest = {
    description: `A request to hand a shift to another employee.`,
    properties: {
        roster_entry_id: {
            type: 'string',
            isRequired: true,
        },
        to_employee_id: {
            type: 'string',
            isRequired: true,
        },
        reason: {
            type: 'string',
            maxLength: 500,
        },
    },
} as const;
