/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Fresh recovery codes. The plaintext is returned exactly once, at generation time, and is not recoverable afterwards.
 */
export type AuthRecoveryCodesResponse = {
    codes: Array<string>;
    generated_at: string;
};

