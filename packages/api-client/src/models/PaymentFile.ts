/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The exported payment file of a finalised run. The file itself is fetched from the download URL, never inlined.
 */
export type PaymentFile = {
    run_id: string;
    format: PaymentFile.format;
    filename: string;
    content_type?: string;
    size_bytes?: number;
    sha256?: string;
    generated_at?: string;
    /**
     * Short lived URL. The file is served by the object storage backend.
     */
    download_url?: string;
};
export namespace PaymentFile {
    export enum format {
        CSV = 'csv',
        CAMT053 = 'camt053',
        SEPA = 'sepa',
        ACH = 'ach',
    }
}

