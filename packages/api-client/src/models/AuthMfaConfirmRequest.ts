/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AuthMfaConfirmRequest = {
    /**
     * The current TOTP code. A wrong code returns 422 `mfa_invalid_code`.
     */
    code: string;
};

