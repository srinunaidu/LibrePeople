/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One result of the configuration assistant: something that is missing or inconsistent, what it means, and what can be done about it.
 */
export type ConfigGap = {
    /**
     * Stable id of the configuration rule.
     */
    rule_id: string;
    severity: ConfigGap.severity;
    /**
     * What is wrong, in words a person can act on.
     */
    message: string;
    /**
     * What has to change: a module, an entity or a field. The fix endpoint takes this value back.
     */
    fix_target: string;
    entity?: string | null;
    /**
     * True when the fix can be applied without further input.
     */
    auto_fixable?: boolean;
    /**
     * True when the gap has already been resolved.
     */
    applied?: boolean;
};
export namespace ConfigGap {
    export enum severity {
        BLOCKING = 'blocking',
        WARNING = 'warning',
        INFO = 'info',
    }
}

