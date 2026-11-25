/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $PaginatedRosterVersions = {
    type: 'all-of',
    contains: [{
        type: 'PaginatedResponse',
    }, {
        properties: {
            items: {
                type: 'array',
                contains: {
                    type: 'RosterVersion',
                },
            },
        },
    }],
} as const;
