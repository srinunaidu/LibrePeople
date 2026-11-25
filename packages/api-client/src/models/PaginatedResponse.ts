/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PageMeta } from './PageMeta';
/**
 * Generic paged collection. Domain variants narrow the `items` array to the entity type of the collection.
 */
export type PaginatedResponse = {
    items: Array<Record<string, any>>;
    meta: PageMeta;
};

