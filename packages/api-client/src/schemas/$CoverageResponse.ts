/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $CoverageResponse = {
    description: `Coverage of the demand for a location and a period, with the gaps that remain.`,
    properties: {
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
        demand_total: {
            type: 'number',
            isRequired: true,
        },
        covered: {
            type: 'number',
            isRequired: true,
        },
        coverage_ratio: {
            type: 'number',
            maximum: 1,
        },
        gaps: {
            type: 'array',
            contains: {
                properties: {
                    work_date: {
                        type: 'string',
                        isRequired: true,
                        format: 'date',
                    },
                    shift_template_id: {
                        type: 'string',
                        isRequired: true,
                    },
                    shortfall: {
                        type: 'number',
                        isRequired: true,
                    },
                },
            },
        },
    },
} as const;
