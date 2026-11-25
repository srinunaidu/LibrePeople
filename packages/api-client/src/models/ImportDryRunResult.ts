/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The outcome of validating a file without writing anything. The `result_hash` covers the counts and the rejected rows; the commit must present a confirmation token that is bound to it.
 */
export type ImportDryRunResult = {
    upload_id: string;
    counts: {
        created: number;
        updated: number;
        unchanged: number;
        rejected: number;
        total: number;
    };
    /**
     * Hash of the dry run outcome. The commit request must quote it and the confirmation token must be bound to it.
     */
    result_hash: string;
    /**
     * Opaque token to present at commit time. It is bound to the result hash; a token that does not match returns 422 `import_confirm_token_invalid`.
     */
    confirmation_token?: string;
    /**
     * A sample of the rejected rows, for display only.
     */
    errors?: Array<{
        row: number;
        field?: string | null;
        reason: string;
        /**
         * A code from the shared code list, for example `import_row_invalid`.
         */
        code?: string;
    }>;
    /**
     * The downloadable row error report.
     */
    errors_csv?: {
        filename: string;
        /**
         * Short lived URL of the CSV with one row per rejected line.
         */
        download_url: string;
        expires_at?: string;
    };
    /**
     * After this moment the confirmation token is no longer valid.
     */
    expires_at?: string;
};

