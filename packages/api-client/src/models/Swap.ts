/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The state of a shift swap.
 */
export type Swap = {
    id: string;
    roster_entry_id?: string;
    from_employee_id?: string;
    to_employee_id?: string;
    requester_id?: string;
    status: Swap.status;
    /**
     * Hard constraints the swap would break. A swap that breaks one is rejected with 409 `swap_violates_constraints`.
     */
    violations?: Array<string>;
    decided_at?: string | null;
    decided_by?: string | null;
};
export namespace Swap {
    export enum status {
        PENDING = 'pending',
        APPROVED = 'approved',
        REJECTED = 'rejected',
    }
}

