/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $EmployeeHistoryEntry = {
    description: `One effective dated change to the employment record. History is append only; a row is closed with \`effective_to\` when a newer change supersedes it.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        field: {
            type: 'string',
            description: `The field that changed, for example \`status\` or \`manager_id\`.`,
            isRequired: true,
        },
        previous_value: {
            type: 'string',
            isNullable: true,
        },
        new_value: {
            type: 'string',
            isNullable: true,
        },
        effective_from: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        effective_to: {
            type: 'string',
            isNullable: true,
            format: 'date',
        },
        reason: {
            type: 'string',
            isNullable: true,
        },
        changed_by: {
            type: 'string',
            description: `Username of the actor that made the change.`,
        },
        changed_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
    },
} as const;
