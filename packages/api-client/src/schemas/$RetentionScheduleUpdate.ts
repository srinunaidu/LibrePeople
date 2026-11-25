/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RetentionScheduleUpdate = {
    properties: {
        entity: {
            type: 'string',
            isRequired: true,
        },
        retention_days: {
            type: 'number',
            isRequired: true,
            minimum: 1,
        },
        action: {
            type: 'Enum',
            isRequired: true,
        },
        legal_hold: {
            type: 'boolean',
        },
    },
} as const;
