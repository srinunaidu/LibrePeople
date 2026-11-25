/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RosterPublishRequest = {
    properties: {
        roster_version_id: {
            type: 'string',
            isRequired: true,
        },
        publish_at: {
            type: 'string',
            description: `Optional. Publish now when omitted.`,
            format: 'date-time',
        },
        notify: {
            type: 'boolean',
            description: `Notify the affected employees after publishing.`,
        },
    },
} as const;
