/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AuthRefreshResponse = {
    access_token: string;
    token_type: AuthRefreshResponse.token_type;
    expires_in: number;
    /**
     * The rotated refresh token. The presented token is invalidated. If an already rotated token is presented again the whole token family is revoked and the response is 401 `refresh_token_reused`.
     */
    refresh_token: string;
};
export namespace AuthRefreshResponse {
    export enum token_type {
        BEARER = 'bearer',
    }
}

