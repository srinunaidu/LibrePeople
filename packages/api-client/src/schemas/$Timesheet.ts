/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $Timesheet = {
    description: `The timesheet of one employee for one period. A period that is locked by a payroll cut off returns 409 \`timesheet_locked\`.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        period_start: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        period_end: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        total_minutes: {
            type: 'number',
        },
        overtime_minutes: {
            type: 'number',
        },
        lines: {
            type: 'array',
            contains: {
                type: 'TimesheetLine',
            },
        },
        submitted_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        approved_by: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
