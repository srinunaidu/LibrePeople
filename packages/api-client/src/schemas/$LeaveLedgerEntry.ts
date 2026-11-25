/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $LeaveLedgerEntry = {
    description: `One immutable movement of a leave balance. The ledger is the audit trail of the balance; the balance itself is a projection of it.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        employee_id: {
            type: 'string',
            isRequired: true,
        },
        leave_type_id: {
            type: 'string',
            isRequired: true,
        },
        effective_date: {
            type: 'string',
            isRequired: true,
            format: 'date',
        },
        direction: {
            type: 'Enum',
            isRequired: true,
        },
        quantity: {
            type: 'number',
            description: `Always positive. The \`direction\` gives the sign.`,
            isRequired: true,
        },
        reason: {
            type: 'string',
            isNullable: true,
        },
        source: {
            type: 'Enum',
        },
        request_id: {
            type: 'string',
            description: `The leave request that caused the movement, when there was one.`,
            isNullable: true,
        },
        running_balance: {
            type: 'number',
            description: `Balance after this movement was applied.`,
        },
    },
} as const;
