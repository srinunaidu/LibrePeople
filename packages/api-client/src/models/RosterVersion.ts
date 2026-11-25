/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A version of the roster for one location and one date range.
 */
export type RosterVersion = {
    id: string;
    location_id: string;
    start_date: string;
    end_date: string;
    status: RosterVersion.status;
    entry_count?: number;
    unfilled_count?: number;
    published_at?: string | null;
    published_by?: string | null;
};
export namespace RosterVersion {
    export enum status {
        DRAFT = 'draft',
        PUBLISHED = 'published',
        SUPERSEDED = 'superseded',
    }
}

