/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Pagination envelope returned with every paged collection.
 */
export type PageMeta = {
    /**
     * The 1-based page that was returned.
     */
    page: number;
    /**
     * The page size the server applied.
     */
    page_size: number;
    /**
     * Total number of rows matching the filter.
     */
    total: number;
    /**
     * Total number of pages available at this page size.
     */
    total_pages: number;
};

