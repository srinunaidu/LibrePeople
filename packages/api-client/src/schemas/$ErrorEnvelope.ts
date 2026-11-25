/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ErrorEnvelope = {
    description: `The top level error body. \`error\` is the only key; no other top level key is permitted.`,
    properties: {
        error: {
            type: 'Error',
            isRequired: true,
        },
    },
} as const;
