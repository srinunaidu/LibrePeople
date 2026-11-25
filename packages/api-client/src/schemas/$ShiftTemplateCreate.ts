/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ShiftTemplateCreate = {
    properties: {
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
            description: `Local end time in \`HH:MM\`.`,
            isRequired: true,
        },
        location_id: {
            type: 'string',
        },
        required_skills: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
        min_rest_minutes: {
            type: 'number',
        },
        crosses_midnight: {
            type: 'boolean',
        },
    },
} as const;
