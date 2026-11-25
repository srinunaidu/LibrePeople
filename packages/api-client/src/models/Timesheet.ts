/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimesheetLine } from './TimesheetLine';
/**
 * The timesheet of one employee for one period. A period that is locked by a payroll cut off returns 409 `timesheet_locked`.
 */
export type Timesheet = {
    id: string;
    employee_id: string;
    period_start: string;
    period_end: string;
    status: Timesheet.status;
    total_minutes?: number;
    overtime_minutes?: number;
    lines?: Array<TimesheetLine>;
    submitted_at?: string | null;
    approved_by?: string | null;
};
export namespace Timesheet {
    export enum status {
        OPEN = 'open',
        SUBMITTED = 'submitted',
        APPROVED = 'approved',
        REJECTED = 'rejected',
        LOCKED = 'locked',
    }
}

