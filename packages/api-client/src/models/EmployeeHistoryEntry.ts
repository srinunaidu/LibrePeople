/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One effective dated change to the employment record. History is append only; a row is closed with `effective_to` when a newer change supersedes it.
 */
export type EmployeeHistoryEntry = {
    id: string;
    /**
     * The field that changed, for example `status` or `manager_id`.
     */
    field: string;
    previous_value?: string | null;
    new_value?: string | null;
    effective_from: string;
    effective_to?: string | null;
    reason?: string | null;
    /**
     * Username of the actor that made the change.
     */
    changed_by?: string;
    changed_at: string;
};

