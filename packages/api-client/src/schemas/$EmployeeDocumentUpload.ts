/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $EmployeeDocumentUpload = {
    description: `The parts of a document upload. The \`file\` part carries the bytes, the other parts carry the metadata.`,
    properties: {
        file: {
            type: 'binary',
            description: `The document. The accepted file types and the size limit are deployment settings, reported by the configuration assistant.`,
            isRequired: true,
            format: 'binary',
        },
        category: {
            type: 'string',
            description: `Free classification, for example \`contract\` or \`id_proof\`.`,
        },
        description: {
            type: 'string',
            maxLength: 500,
        },
        effective_from: {
            type: 'string',
            description: `Date the document takes effect from.`,
            format: 'date',
        },
    },
} as const;
