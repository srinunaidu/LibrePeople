/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The launch of this deployment. The call is idempotent: launching an already launched deployment returns the same result.
 */
export type OnboardingLaunchRequest = {
    /**
     * Must be true. Guards against an accidental launch.
     */
    confirm?: boolean;
    /**
     * Report what the launch would do without doing it.
     */
    dry_run?: boolean;
};

