/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A set of non working days for one location and one year. The whole set is applied in one transaction.
 */
export type HolidayBulkCreate = {
    year: number;
    location_id: string;
    /**
     * Optional jurisdiction label to attach to every created holiday.
     */
    jurisdiction?: string;
    holidays: Array<{
        name: string;
        date: string;
        is_public?: boolean;
    }>;
};

