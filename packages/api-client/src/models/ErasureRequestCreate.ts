/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ErasureRequestCreate = {
    /**
     * Required when `subject_type` is `employee`.
     */
    employee_id?: string;
    subject_type: ErasureRequestCreate.subject_type;
    legal_basis?: string;
    reason?: string;
};
export namespace ErasureRequestCreate {
    export enum subject_type {
        EMPLOYEE = 'employee',
        APPLICANT = 'applicant',
        CONTRACTOR = 'contractor',
    }
}

