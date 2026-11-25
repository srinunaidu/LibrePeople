/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AuthLoginResponse = {
    /**
     * JWT access token. Send as `Authorization: Bearer <token>`.
     */
    access_token: string;
    token_type: AuthLoginResponse.token_type;
    /**
     * Access token lifetime in seconds.
     */
    expires_in: number;
    /**
     * Role granted to the account.
     */
    role: string;
    /**
     * True when the account still has to set its own password. The token is valid but privileged calls return 401 `password_change_required`.
     */
    must_change_password: boolean;
    /**
     * Refresh token, issued when refresh token rotation is enabled. Presented to `POST /auth/refresh`, never to any other endpoint.
     */
    refresh_token?: string;
};
export namespace AuthLoginResponse {
    export enum token_type {
        BEARER = 'bearer',
    }
}

