/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ConfigGap = {
    description: `One result of the configuration assistant: something that is missing or inconsistent, what it means, and what can be done about it.`,
    properties: {
        rule_id: {
            type: 'string',
            description: `Stable id of the configuration rule.`,
            isRequired: true,
        },
        severity: {
            type: 'Enum',
            isRequired: true,
        },
        message: {
            type: 'string',
            description: `What is wrong, in words a person can act on.`,
            isRequired: true,
        },
        fix_target: {
            type: 'string',
            description: `What has to change: a module, an entity or a field. The fix endpoint takes this value back.`,
            isRequired: true,
        },
        entity: {
            type: 'string',
            isNullable: true,
        },
        auto_fixable: {
            type: 'boolean',
            description: `True when the fix can be applied without further input.`,
        },
        applied: {
            type: 'boolean',
            description: `True when the gap has already been resolved.`,
        },
    },
} as const;
