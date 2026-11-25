/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * What to forecast, how, and for how long. The series is a metric of this deployment, not a cross tenant query.
 */
export type ForecastRunCreate = {
    /**
     * The metric to forecast.
     */
    series: {
        /**
         * Metric key, for example `headcount` or `absence_rate`.
         */
        metric: string;
        /**
         * Optional dimension filters inside this deployment.
         */
        filters?: Record<string, any>;
        granularity?: ForecastRunCreate.granularity;
    };
    /**
     * Forecast method. `auto` lets the server pick from the data. Every other value is an explicit override and is recorded in the result.
     */
    method?: ForecastRunCreate.method;
    /**
     * Number of periods to forecast.
     */
    horizon: number;
    /**
     * Number of holdout periods used to measure the error.
     */
    backtest_window?: number;
    /**
     * Minimum history the method needs. Below it the run is still created but is flagged `insufficient_history` and the forecast values are omitted.
     */
    min_history_weeks?: number;
};
export namespace ForecastRunCreate {
    export enum granularity {
        DAY = 'day',
        WEEK = 'week',
        MONTH = 'month',
    }
    /**
     * Forecast method. `auto` lets the server pick from the data. Every other value is an explicit override and is recorded in the result.
     */
    export enum method {
        AUTO = 'auto',
        EXPONENTIAL_SMOOTHING = 'exponential_smoothing',
        HOLT_WINTERS = 'holt_winters',
        MOVING_AVERAGE = 'moving_average',
        SEASONAL_NAIVE = 'seasonal_naive',
        LINEAR_REGRESSION = 'linear_regression',
    }
}

