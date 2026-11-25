/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LeaveRequestCreate = {
    leave_type_id: string;
    start_date: string;
    end_date: string;
    /**
     * Optional. When omitted the server derives the quantity from the leave calendar of the employee.
     */
    quantity?: number;
    reason?: string;
    half_day?: boolean;
    notes?: string;
};

