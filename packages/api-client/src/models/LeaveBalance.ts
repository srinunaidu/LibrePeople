/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The leave balance of one employee for one leave type and one year. Balances are derived from the ledger; the numbers here are the projection at the reporting date.
 */
export type LeaveBalance = {
    employee_id: string;
    leave_type_id: string;
    leave_type_code?: string;
    year: number;
    entitled: number;
    taken?: number;
    pending?: number;
    available: number;
    /**
     * Date the balance was computed.
     */
    as_of?: string;
};

