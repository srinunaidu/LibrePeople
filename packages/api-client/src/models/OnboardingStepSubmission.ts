/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The payload of one setup step. The accepted fields depend on the step named in the path; a field the step does not know is rejected with 422 `validation_error`.
 */
export type OnboardingStepSubmission = {
    /**
     * The step payload. Shape depends on the step.
     */
    data?: Record<string, any>;
    /**
     * Mark an optional step as skipped. A required step cannot be skipped.
     */
    skip?: boolean;
    /**
     * Recompute the downstream steps after this submission.
     */
    confirm?: boolean;
};

