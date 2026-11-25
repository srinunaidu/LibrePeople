/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type DsarExportCreate = {
    employee_id?: string;
    subject_type: DsarExportCreate.subject_type;
    format?: DsarExportCreate.format;
};
export namespace DsarExportCreate {
    export enum subject_type {
        EMPLOYEE = 'employee',
        APPLICANT = 'applicant',
        CONTRACTOR = 'contractor',
    }
    export enum format {
        JSON = 'json',
        ZIP = 'zip',
    }
}

