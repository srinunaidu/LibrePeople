/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RosterVersion = {
    description: `A version of the roster for one location and one date range.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        location_id: {
            type: 'string',
            isRequired: true,
        },
        start_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        end_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        entry_count: {
            type: 'number',
        },
        unfilled_count: {
            type: 'number',
        },
        published_at: {
            type: 'string',
            isNullable: true,
            format: 'date-time',
        },
        published_by: {
            type: 'string',
            isNullable: true,
        },
    },
} as const;
