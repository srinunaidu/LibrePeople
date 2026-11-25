/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PageMeta = {
    description: `Pagination envelope returned with every paged collection.`,
    properties: {
        page: {
            type: 'number',
            description: `The 1-based page that was returned.`,
            isRequired: true,
            minimum: 1,
        },
        page_size: {
            type: 'number',
            description: `The page size the server applied.`,
            isRequired: true,
            maximum: 200,
            minimum: 1,
        },
        total: {
            type: 'number',
            description: `Total number of rows matching the filter.`,
            isRequired: true,
        },
        total_pages: {
            type: 'number',
            description: `Total number of pages available at this page size.`,
            isRequired: true,
        },
    },
} as const;
