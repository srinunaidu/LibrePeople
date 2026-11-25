/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A requirement the solver could not satisfy, and why. `causes` is machine readable so a client can explain the gap without parsing prose.
 */
export type UnfilledSlot = {
    shift_template_id: string;
    work_date: string;
    required_headcount: number;
    filled: number;
    /**
     * Why the slot stayed open, for example `no_eligible_employee`, `hard_constraint_conflict` or `time_limit_reached`.
     */
    causes: Array<string>;
};

