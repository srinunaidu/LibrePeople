/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A named set of pay components used by pay runs.
 */
export type PayProfile = {
    id: string;
    name: string;
    /**
     * ISO 4217 currency code of the profile.
     */
    currency?: string;
    pay_frequency?: PayProfile.pay_frequency;
    component_ids?: Array<string>;
    active?: boolean;
};
export namespace PayProfile {
    export enum pay_frequency {
        WEEKLY = 'weekly',
        BIWEEKLY = 'biweekly',
        SEMIMONTHLY = 'semimonthly',
        MONTHLY = 'monthly',
    }
}

