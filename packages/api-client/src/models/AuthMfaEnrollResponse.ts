/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * TOTP enrolment material. The shared secret is returned exactly once, at enrolment time. It is never shown again and never included in any later response.
 */
export type AuthMfaEnrollResponse = {
    /**
     * Base32 TOTP shared secret. Shown once.
     */
    secret: string;
    /**
     * The `otpauth://` URI to scan into an authenticator app.
     */
    otpauth_uri: string;
    digits?: number;
    /**
     * TOTP time step in seconds.
     */
    period?: number;
    algorithm?: string;
};

