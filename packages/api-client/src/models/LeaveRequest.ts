/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A leave request and its decision state.
 */
export type LeaveRequest = {
    id: string;
    employee_id: string;
    leave_type_id: string;
    start_date: string;
    end_date: string;
    quantity?: number;
    unit?: LeaveRequest.unit;
    status: LeaveRequest.status;
    reason?: string | null;
    created_at?: string;
    decided_at?: string | null;
    decided_by?: string | null;
    decision_note?: string | null;
};
export namespace LeaveRequest {
    export enum unit {
        DAYS = 'days',
        HOURS = 'hours',
    }
    export enum status {
        PENDING = 'pending',
        APPROVED = 'approved',
        REJECTED = 'rejected',
        CANCELLED = 'cancelled',
    }
}

