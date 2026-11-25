/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A user account of this deployment.
 */
export type AuthUser = {
    id: string;
    username: string;
    email?: string;
    /**
     * Role held by the account.
     */
    role: string;
    /**
     * A disabled account cannot authenticate.
     */
    is_active: boolean;
    must_change_password?: boolean;
    mfa_enabled?: boolean;
    created_at?: string;
    last_login_at?: string;
};

