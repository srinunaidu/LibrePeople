/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A non working day for one location. The list is maintained by the customer; statutory dates are never hard coded by the platform.
 */
export type Holiday = {
    id: string;
    name: string;
    date: string;
    location_id: string;
    /**
     * Optional jurisdiction label, used to match a rule pack.
     */
    jurisdiction?: string | null;
    is_public?: boolean;
};

