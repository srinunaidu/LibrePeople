/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RosterEntry } from './RosterEntry';
import type { SolverMetadata } from './SolverMetadata';
import type { UnfilledSlot } from './UnfilledSlot';
/**
 * A candidate roster plus everything the solver could not fill. The candidate is not live until it is published.
 */
export type RosterGenerateResponse = {
    /**
     * Version the candidates belong to. The version stays in `draft`.
     */
    roster_version_id: string;
    candidates: Array<RosterEntry>;
    unfilled: Array<UnfilledSlot>;
    solver: SolverMetadata;
    warnings?: Array<string>;
};

