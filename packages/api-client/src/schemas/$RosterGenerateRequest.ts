/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RosterGenerateRequest = {
    description: `The input of the roster solver: how many people are needed, what must hold, and how the solver should trade the objectives off. A request that contradicts itself returns 422 \`validation_error\`.`,
    properties: {
        start_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        end_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        location_id: {
            type: 'string',
            isRequired: true,
        },
        demand: {
            type: 'array',
            contains: {
                properties: {
                    shift_template_id: {
                        type: 'string',
                        isRequired: true,
                    },
                    work_date: {
                        type: 'string',
                        description: `Optional. When omitted the demand applies to every date in the range.`,
                        format: 'date',
                    },
                    required_headcount: {
                        type: 'number',
                        isRequired: true,
                    },
                },
            },
            isRequired: true,
        },
        constraints: {
            description: `Hard constraints. The solver never breaks these; when they cannot all hold the response carries unfilled slots and their causes.`,
            properties: {
                max_shifts_per_employee: {
                    type: 'number',
                },
                max_weekly_hours: {
                    type: 'number',
                },
                min_rest_minutes: {
                    type: 'number',
                },
                required_skills: {
                    type: 'array',
                    contains: {
                        type: 'string',
                    },
                },
                exclude_employees: {
                    type: 'array',
                    contains: {
                        type: 'string',
                    },
                },
                respect_leave: {
                    type: 'boolean',
                    description: `Do not assign an employee who is on approved leave.`,
                },
            },
        },
        weights: {
            description: `Relative weight of each objective. The solver minimises the weighted sum. A weight of zero removes the objective.`,
            properties: {
                labour_cost: {
                    type: 'number',
                },
                fairness: {
                    type: 'number',
                },
                preference: {
                    type: 'number',
                },
                overtime: {
                    type: 'number',
                },
            },
        },
        time_limit_seconds: {
            type: 'number',
            description: `Solver time limit. Exceeding it returns 503 \`solver_timeout\` with the unmet slot list.`,
            minimum: 1,
        },
    },
} as const;
