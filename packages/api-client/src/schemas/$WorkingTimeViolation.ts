/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $WorkingTimeViolation = {
    description: `A detected breach of the configured working time rules, for example a missing break or a daily maximum overrun.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        work_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        kind: {
            type: 'string',
            description: `Machine readable violation kind, for example \`missing_break\` or \`max_daily_exceeded\`.`,
            isRequired: true,
        },
        severity: {
            type: 'Enum',
            isRequired: true,
        },
        minutes: {
            type: 'number',
            description: `Minutes involved in the violation.`,
        },
        detected_at: {
            type: 'string',
            format: 'date-time',
        },
        resolved: {
            type: 'boolean',
        },
    },
} as const;
