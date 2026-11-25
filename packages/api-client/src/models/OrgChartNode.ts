/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A node of the reporting tree.
 */
export type OrgChartNode = {
    employee_id: string;
    /**
     * Display name of the employee. Not a credential.
     */
    name: string;
    position_id?: string | null;
    department_id?: string | null;
    manager_id?: string | null;
    direct_reports?: Array<OrgChartNode>;
};

