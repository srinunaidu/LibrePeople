/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $HolidayBulkCreate = {
    description: `A set of non working days for one location and one year. The whole set is applied in one transaction.`,
    properties: {
        year: {
            type: 'number',
            isRequired: true,
            maximum: 2100,
            minimum: 2000,
        },
        location_id: {
            type: 'string',
            isRequired: true,
        },
        jurisdiction: {
            type: 'string',
            description: `Optional jurisdiction label to attach to every created holiday.`,
        },
        holidays: {
            type: 'array',
            contains: {
                properties: {
                    name: {
                        type: 'string',
                        isRequired: true,
                    },
                    date: {
                        type: 'string',
                        isRequired: true,
                        format: 'date',
                    },
                    is_public: {
                        type: 'boolean',
                    },
                },
            },
            isRequired: true,
        },
    },
} as const;
