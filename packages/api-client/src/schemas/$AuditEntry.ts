/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $AuditEntry = {
    description: `One link of the audit chain. Each entry hashes the previous entry, so a removed or edited row breaks the chain at that point.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        actor_id: {
            type: 'string',
            isNullable: true,
        },
        actor_username: {
            type: 'string',
            isNullable: true,
        },
        action: {
            type: 'string',
            description: `What was done, for example \`leave.approve\`.`,
            isRequired: true,
        },
        entity_type: {
            type: 'string',
            isRequired: true,
        },
        entity_id: {
            type: 'string',
            isNullable: true,
        },
        outcome: {
            type: 'Enum',
        },
        request_id: {
            type: 'string',
            isNullable: true,
        },
        occurred_at: {
            type: 'string',
            isRequired: true,
            format: 'date-time',
        },
        previous_hash: {
            type: 'string',
            isNullable: true,
        },
        entry_hash: {
            type: 'string',
            description: `Hash of this entry, including the hash of the previous one.`,
            isRequired: true,
        },
    },
} as const;
