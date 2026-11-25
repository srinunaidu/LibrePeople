/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RosterEntry = {
    description: `One assigned shift in a roster version.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        roster_version_id: {
            type: 'string',
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        shift_template_id: {
            type: 'string',
            isRequired: true,
        },
        work_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        start_time: {
            type: 'string',
        },
        end_time: {
            type: 'string',
        },
        minutes: {
            type: 'number',
        },
        status: {
            type: 'Enum',
        },
    },
} as const;
