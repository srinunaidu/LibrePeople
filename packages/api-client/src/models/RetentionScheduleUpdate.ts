/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type RetentionScheduleUpdate = {
    entity: string;
    retention_days: number;
    action: RetentionScheduleUpdate.action;
    legal_hold?: boolean;
};
export namespace RetentionScheduleUpdate {
    export enum action {
        PURGE = 'purge',
        ANONYMISE = 'anonymise',
        ARCHIVE = 'archive',
    }
}

