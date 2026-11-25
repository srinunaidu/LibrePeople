/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The exact columns one import entity expects. A file with an unknown column is rejected with 422 `import_header_unknown`; the list here is what a client must build the file from.
 */
export type ImportTemplate = {
    entity: string;
    version: string;
    delimiter?: string;
    encoding?: string;
    columns: Array<{
        /**
         * Exact header text expected in the file.
         */
        name: string;
        required: boolean;
        type: 'string' | 'integer' | 'decimal' | 'date' | 'datetime' | 'boolean' | 'enum';
        description?: string;
        allowed_values?: Array<string>;
        max_length?: number;
    }>;
};

