/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PaginatedResponse = {
    description: `Generic paged collection. Domain variants narrow the \`items\` array to the entity type of the collection.`,
    properties: {
        items: {
            type: 'array',
            contains: {
                type: 'dictionary',
                contains: {
                    properties: {
                    },
                },
            },
            isRequired: true,
        },
        meta: {
            type: 'PageMeta',
            isRequired: true,
        },
    },
} as const;
