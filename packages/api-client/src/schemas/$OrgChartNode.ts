/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $OrgChartNode = {
    description: `A node of the reporting tree.`,
    properties: {
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            description: `Display name of the employee. Not a credential.`,
            isRequired: true,
        },
        position_id: {
            type: 'string',
            isNullable: true,
        },
        department_id: {
            type: 'string',
            isNullable: true,
        },
        manager_id: {
            type: 'string',
            isNullable: true,
        },
        direct_reports: {
            type: 'array',
            contains: {
                type: 'OrgChartNode',
            },
        },
    },
} as const;
