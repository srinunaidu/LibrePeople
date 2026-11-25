/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $TimesheetLine = {
    properties: {
        entry_id: {
            type: 'string',
            isRequired: true,
        },
        work_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        minutes: {
            type: 'number',
            isRequired: true,
        },
        source: {
            type: 'string',
        },
    },
} as const;
