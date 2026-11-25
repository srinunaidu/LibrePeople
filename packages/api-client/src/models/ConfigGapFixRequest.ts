/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The request that resolves one configuration gap.
 */
export type ConfigGapFixRequest = {
    /**
     * Values the fix needs. Empty for an auto fix.
     */
    parameters?: Record<string, any>;
    /**
     * Report what the fix would do without applying it.
     */
    dry_run?: boolean;
};

