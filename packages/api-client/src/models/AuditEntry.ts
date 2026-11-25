/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One link of the audit chain. Each entry hashes the previous entry, so a removed or edited row breaks the chain at that point.
 */
export type AuditEntry = {
    id: string;
    actor_id?: string | null;
    actor_username?: string | null;
    /**
     * What was done, for example `leave.approve`.
     */
    action: string;
    entity_type: string;
    entity_id?: string | null;
    outcome?: AuditEntry.outcome;
    request_id?: string | null;
    occurred_at: string;
    previous_hash?: string | null;
    /**
     * Hash of this entry, including the hash of the previous one.
     */
    entry_hash: string;
};
export namespace AuditEntry {
    export enum outcome {
        SUCCESS = 'success',
        FAILURE = 'failure',
    }
}

