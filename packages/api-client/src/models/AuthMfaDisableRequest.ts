/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AuthMfaDisableRequest = {
    /**
     * One unused recovery code. A wrong code returns 422 `mfa_recovery_code_invalid` and MFA stays enabled.
     */
    recovery_code: string;
};

