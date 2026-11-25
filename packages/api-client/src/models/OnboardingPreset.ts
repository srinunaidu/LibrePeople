/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A starting configuration for a kind of business: the modules to enable, the default roles and the recommended settings.
 */
export type OnboardingPreset = {
    id: string;
    name: string;
    description?: string;
    industry?: string | null;
    modules: Array<string>;
    default_roles?: Array<Record<string, any>>;
    recommended_settings?: Record<string, any>;
};

