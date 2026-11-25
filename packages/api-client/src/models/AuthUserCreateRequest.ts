/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AuthUserCreateRequest = {
    username: string;
    email: string;
    /**
     * Must satisfy the deployment password policy. A rejected password returns 422 `password_policy_violation`; a password on the local breached list returns 422 `password_breached`.
     */
    password: string;
    /**
     * Role to grant. Only an administrator may call this endpoint.
     */
    role: string;
    /**
     * When true the account is created with `must_change_password` set and no password is delivered to the user.
     */
    send_invite?: boolean;
};

