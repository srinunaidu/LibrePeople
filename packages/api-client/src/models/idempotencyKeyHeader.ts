/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Caller-generated key (1-200 characters) that makes this mutation safe to retry. Replaying the same key with the same payload returns the original result; replaying it with a different payload is a 409 `idempotency_key_reuse`.
 */
export type idempotencyKeyHeader = string;
