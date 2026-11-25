/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A rule pack: the versioned rule set of one jurisdiction. A payroll run may only be calculated when the pack of its jurisdiction is `verified`.
 */
export type RulePack = {
    id: string;
    name: string;
    jurisdiction: string;
    version: string;
    status: RulePack.status;
    /**
     * Where the pack came from.
     */
    source?: {
        type?: RulePack.type;
        reference?: string;
        installed_at?: string;
    };
    /**
     * The verification state of the pack.
     */
    verification?: {
        verified_at?: string | null;
        verified_by?: string | null;
        checks?: Array<Record<string, any>>;
    };
    /**
     * The signature of the pack.
     */
    signing?: {
        algorithm?: string;
        key_id?: string;
        signature?: string;
        signed_at?: string;
    };
    /**
     * Hash of the pack contents.
     */
    checksum?: string;
};
export namespace RulePack {
    export enum status {
        DRAFT = 'draft',
        VERIFIED = 'verified',
        DEPRECATED = 'deprecated',
        REJECTED = 'rejected',
    }
    export enum type {
        BUNDLED = 'bundled',
        UPLOADED = 'uploaded',
        CATALOGUE = 'catalogue',
    }
}

