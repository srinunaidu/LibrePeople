/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ShiftTemplateCreate = {
    name: string;
    /**
     * Local start time in `HH:MM`.
     */
    start_time: string;
    /**
     * Local end time in `HH:MM`.
     */
    end_time: string;
    location_id?: string;
    required_skills?: Array<string>;
    min_rest_minutes?: number;
    crosses_midnight?: boolean;
};

