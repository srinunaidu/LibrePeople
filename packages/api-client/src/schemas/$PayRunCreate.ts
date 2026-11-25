/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PayRunCreate = {
    properties: {
        period_id: {
            type: 'string',
            isRequired: true,
        },
        jurisdiction: {
            type: 'string',
            description: `Jurisdiction that determines the rule pack. A jurisdiction with no pack returns 422 \`rule_pack_missing\`.`,
            isRequired: true,
        },
        employee_ids: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
        run_type: {
            type: 'Enum',
        },
        currency: {
            type: 'string',
        },
    },
} as const;
