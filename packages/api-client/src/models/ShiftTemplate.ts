/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A reusable shift definition.
 */
export type ShiftTemplate = {
    id: string;
    name: string;
    /**
     * Local start time in `HH:MM`.
     */
    start_time: string;
    /**
     * Local end time in `HH:MM`. May be earlier than the start when the shift crosses midnight.
     */
    end_time: string;
    duration_minutes?: number;
    crosses_midnight?: boolean;
    location_id?: string | null;
    required_skills?: Array<string>;
    /**
     * Minimum rest between two shifts of the same employee.
     */
    min_rest_minutes?: number;
    version?: number;
};

