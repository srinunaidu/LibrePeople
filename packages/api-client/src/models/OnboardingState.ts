/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The resumable setup state machine of this deployment. Every step can be submitted again; the state records what is done and what is next.
 */
export type OnboardingState = {
    /**
     * The step the deployment is waiting on. Null when the setup is finished.
     */
    current_step: OnboardingState.current_step | null;
    completed_steps: Array<'company_profile' | 'business_type' | 'modules' | 'import' | 'roles' | 'review' | 'launch'>;
    steps?: Array<{
        id: string;
        title?: string;
        status: 'pending' | 'in_progress' | 'complete' | 'skipped';
        required?: boolean;
        completed_at?: string | null;
    }>;
    progress: {
        completed: number;
        total: number;
        percent?: number;
    };
    started_at?: string;
    updated_at?: string;
    /**
     * True when the deployment has been launched and is ready for use.
     */
    deployment_ready?: boolean;
};
export namespace OnboardingState {
    /**
     * The step the deployment is waiting on. Null when the setup is finished.
     */
    export enum current_step {
        COMPANY_PROFILE = 'company_profile',
        BUSINESS_TYPE = 'business_type',
        MODULES = 'modules',
        IMPORT = 'import',
        ROLES = 'roles',
        REVIEW = 'review',
        LAUNCH = 'launch',
    }
}

