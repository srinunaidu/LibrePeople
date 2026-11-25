/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AuthPasswordChangeRequest = {
    current_password: string;
    /**
     * Must satisfy the password policy and must not repeat one of the last N passwords. Failures return 422 `password_policy_violation`, `password_reuse` or `password_breached`.
     */
    new_password: string;
};

