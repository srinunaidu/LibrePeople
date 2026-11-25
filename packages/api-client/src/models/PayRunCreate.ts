/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type PayRunCreate = {
    period_id: string;
    /**
     * Jurisdiction that determines the rule pack. A jurisdiction with no pack returns 422 `rule_pack_missing`.
     */
    jurisdiction: string;
    /**
     * Subset of employees to include. All active employees when omitted.
     */
    employee_ids?: Array<string>;
    run_type?: PayRunCreate.run_type;
    currency?: string;
};
export namespace PayRunCreate {
    export enum run_type {
        REGULAR = 'regular',
        OFF_CYCLE = 'off_cycle',
        CORRECTION = 'correction',
    }
}

