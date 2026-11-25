/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ImportUploadRequest = {
    description: `The parts of an import upload. The \`file\` part carries the bytes, the other parts carry the metadata.`,
    properties: {
        file: {
            type: 'binary',
            description: `The CSV file to import.`,
            isRequired: true,
            format: 'binary',
        },
        entity: {
            type: 'string',
            description: `The entity the file targets, for example \`employee\`. When it is omitted the server derives it from the headers of the file.`,
        },
        template_version: {
            type: 'string',
            description: `The version of the template the caller built the file from. It is reported back on the upload so a mismatch can be spotted.`,
        },
        dry_run: {
            type: 'boolean',
            description: `Validate the file as soon as it is uploaded instead of waiting for an explicit dry run.`,
        },
    },
} as const;
