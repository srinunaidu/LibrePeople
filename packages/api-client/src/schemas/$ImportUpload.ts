/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImportUpload = {
    description: `An uploaded import file, before it is dry run or committed. The upload expires if it is not used.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        entity: {
            type: 'string',
            description: `The entity the file targets, for example \`employee\`.`,
            isRequired: true,
        },
        filename: {
            type: 'string',
            isRequired: true,
        },
        content_type: {
            type: 'string',
        },
        size_bytes: {
            type: 'number',
        },
        checksum: {
            type: 'string',
        },
        status: {
            type: 'Enum',
            isRequired: true,
        },
        template_version: {
            type: 'string',
            description: `Version of the template the file was validated against.`,
        },
        uploaded_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
        uploaded_by: {
            type: 'string',
        },
        expires_at: {
            type: 'string',
            format: 'date-time',
        },
    },
} as const;
