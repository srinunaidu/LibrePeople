/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImportTemplate = {
    description: `The exact columns one import entity expects. A file with an unknown column is rejected with 422 \`import_header_unknown\`; the list here is what a client must build the file from.`,
    properties: {
        entity: {
            type: 'string',
            isRequired: true,
        },
        version: {
            type: 'string',
            isRequired: true,
        },
        delimiter: {
            type: 'string',
        },
        encoding: {
            type: 'string',
        },
        columns: {
            type: 'array',
            contains: {
                properties: {
                    name: {
                        type: 'string',
                        description: `Exact header text expected in the file.`,
                        isRequired: true,
                    },
                    required: {
                        type: 'boolean',
                        isRequired: true,
                    },
                    type: {
                        type: 'Enum',
                        isRequired: true,
                    },
                    description: {
                        type: 'string',
                    },
                    allowed_values: {
                        type: 'array',
                        contains: {
                            type: 'string',
                        },
                    },
                    max_length: {
                        type: 'number',
                    },
                },
            },
            isRequired: true,
        },
    },
} as const;
