/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type RosterPublishRequest = {
    roster_version_id: string;
    /**
     * Optional. Publish now when omitted.
     */
    publish_at?: string;
    /**
     * Notify the affected employees after publishing.
     */
    notify?: boolean;
};

