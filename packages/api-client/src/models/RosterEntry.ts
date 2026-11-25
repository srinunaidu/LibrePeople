/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One assigned shift in a roster version.
 */
export type RosterEntry = {
    id: string;
    roster_version_id?: string;
    employee_id: string;
    shift_template_id: string;
    work_date: string;
    start_time?: string;
    end_time?: string;
    minutes?: number;
    status?: RosterEntry.status;
};
export namespace RosterEntry {
    export enum status {
        DRAFT = 'draft',
        PUBLISHED = 'published',
        LOCKED = 'locked',
    }
}

