/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ShiftTemplate = {
    description: `A reusable shift definition.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        start_time: {
            type: 'string',
            description: `Local start time in \`HH:MM\`.`,
            isRequired: true,
        },
        end_time: {
            type: 'string',
            description: `Local end time in \`HH:MM\`. May be earlier than the start when the shift crosses midnight.`,
            isRequired: true,
        },
        duration_minutes: {
            type: 'number',
            minimum: 1,
        },
        crosses_midnight: {
            type: 'boolean',
        },
        location_id: {
            type: 'string',
            isNullable: true,
        },
        required_skills: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
        min_rest_minutes: {
            type: 'number',
            description: `Minimum rest between two shifts of the same employee.`,
        },
        version: {
            type: 'number',
            minimum: 1,
        },
    },
} as const;
