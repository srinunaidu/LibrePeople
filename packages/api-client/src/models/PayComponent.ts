/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One element of a pay profile.
 */
export type PayComponent = {
    id: string;
    code: string;
    name: string;
    category: PayComponent.category;
    taxable?: boolean;
    calculation_type?: PayComponent.calculation_type;
    /**
     * Opaque calculation expression. The customer owns the formula; the platform does not publish statutory values.
     */
    calculation_value?: string;
    /**
     * Order in which the component is calculated.
     */
    sequence?: number;
};
export namespace PayComponent {
    export enum category {
        EARNING = 'earning',
        DEDUCTION = 'deduction',
        EMPLOYER_CONTRIBUTION = 'employer_contribution',
    }
    export enum calculation_type {
        FIXED = 'fixed',
        PERCENTAGE = 'percentage',
        FORMULA = 'formula',
    }
}

