/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The input of the roster solver: how many people are needed, what must hold, and how the solver should trade the objectives off. A request that contradicts itself returns 422 `validation_error`.
 */
export type RosterGenerateRequest = {
    start_date: string;
    end_date: string;
    location_id: string;
    /**
     * Required headcount per shift template and date.
     */
    demand: Array<{
        shift_template_id: string;
        /**
         * Optional. When omitted the demand applies to every date in the range.
         */
        work_date?: string;
        required_headcount: number;
    }>;
    /**
     * Hard constraints. The solver never breaks these; when they cannot all hold the response carries unfilled slots and their causes.
     */
    constraints?: {
        max_shifts_per_employee?: number;
        max_weekly_hours?: number;
        min_rest_minutes?: number;
        required_skills?: Array<string>;
        exclude_employees?: Array<string>;
        /**
         * Do not assign an employee who is on approved leave.
         */
        respect_leave?: boolean;
    };
    /**
     * Relative weight of each objective. The solver minimises the weighted sum. A weight of zero removes the objective.
     */
    weights?: {
        labour_cost?: number;
        fairness?: number;
        preference?: number;
        overtime?: number;
    };
    /**
     * Solver time limit. Exceeding it returns 503 `solver_timeout` with the unmet slot list.
     */
    time_limit_seconds?: number;
};

