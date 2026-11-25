/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RulePack = {
    description: `A rule pack: the versioned rule set of one jurisdiction. A payroll run may only be calculated when the pack of its jurisdiction is \`verified\`.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        name: {
            type: 'string',
            isRequired: true,
        },
        jurisdiction: {
            type: 'string',
            isRequired: true,
        },
        version: {
            type: 'string',
            isRequired: true,
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        source: {
            description: `Where the pack came from.`,
            properties: {
                type: {
                    type: 'Enum',
                },
                reference: {
                    type: 'string',
                },
                installed_at: {
                    type: 'string',
                    format: 'date-time',
                },
            },
        },
        verification: {
            description: `The verification state of the pack.`,
            properties: {
                verified_at: {
                    type: 'string',
                    isNullable: true,
                    format: 'date-time',
                },
                verified_by: {
                    type: 'string',
                    isNullable: true,
                },
                checks: {
                    type: 'array',
                    contains: {
                        type: 'dictionary',
                        contains: {
                            properties: {
                            },
                        },
                    },
                },
            },
        },
        signing: {
            description: `The signature of the pack.`,
            properties: {
                algorithm: {
                    type: 'string',
                },
                key_id: {
                    type: 'string',
                },
                signature: {
                    type: 'string',
                },
                signed_at: {
                    type: 'string',
                    format: 'date-time',
                },
            },
        },
        checksum: {
            type: 'string',
            description: `Hash of the pack contents.`,
        },
    },
} as const;
