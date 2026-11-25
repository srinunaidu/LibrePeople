/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A request to hand a shift to another employee.
 */
export type SwapRequest = {
    roster_entry_id: string;
    to_employee_id: string;
    reason?: string;
};

