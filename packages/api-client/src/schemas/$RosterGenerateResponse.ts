/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $RosterGenerateResponse = {
    description: `A candidate roster plus everything the solver could not fill. The candidate is not live until it is published.`,
    properties: {
        roster_version_id: {
            type: 'string',
            description: `Version the candidates belong to. The version stays in \`draft\`.`,
            isRequired: true,
        },
        candidates: {
            type: 'array',
            contains: {
                type: 'RosterEntry',
            },
            isRequired: true,
        },
        unfilled: {
            type: 'array',
            contains: {
                type: 'UnfilledSlot',
            },
            isRequired: true,
        },
        solver: {
            type: 'SolverMetadata',
            isRequired: true,
        },
        warnings: {
            type: 'array',
            contains: {
                type: 'string',
            },
        },
    },
} as const;
