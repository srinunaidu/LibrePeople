/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type OnboardingLaunchResponse = {
    launched: boolean;
    /**
     * True when the deployment was already launched. The call was a no op.
     */
    already_launched?: boolean;
    /**
     * Background job that prepares the deployment, when there is one.
     */
    job_id?: string | null;
};

