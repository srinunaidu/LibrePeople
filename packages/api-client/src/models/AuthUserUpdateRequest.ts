/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Partial update. `role` changes are audited; setting `is_active` to false revokes every live session of that account.
 */
export type AuthUserUpdateRequest = {
    email?: string;
    role?: string;
    is_active?: boolean;
};

