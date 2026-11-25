/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * One forecast run, with everything needed to judge it: the method that was used, the window it was fitted on, the measured error on a holdout, the confidence band, and a hash of the input so the run can be reproduced.
 */
export type ForecastRun = {
    id: string;
    series: Record<string, any>;
    /**
     * The method that was actually used. Resolved when the request said `auto`.
     */
    method: string;
    /**
     * Version of the forecasting implementation that produced the result.
     */
    method_version?: string;
    /**
     * The observations the model was fitted on.
     */
    data_window?: {
        start: string;
        end: string;
        observations: number;
    };
    /**
     * The measured error on a holdout. `mape` is the mean absolute percentage error, `mase` the mean absolute scaled error.
     */
    backtest?: {
        /**
         * Mean absolute percentage error over the holdout. Null when it cannot be computed.
         */
        mape: number | null;
        /**
         * Mean absolute scaled error over the holdout. Null when it cannot be computed.
         */
        mase: number | null;
        /**
         * Number of periods held out of the fit.
         */
        holdout_length: number;
        holdout_start?: string;
        holdout_end?: string;
    };
    /**
     * The interval the forecast is stated with.
     */
    confidence_band?: {
        /**
         * Coverage of the interval, for example 0.8.
         */
        level?: number;
        /**
         * How the band was derived, for example `residual_variance`.
         */
        method?: string;
    };
    forecast?: Array<{
        period: string;
        value: number;
        lower?: number;
        upper?: number;
    }>;
    /**
     * Hash of the exact input the run was computed from. The same input hash means the same run.
     */
    input_hash: string;
    /**
     * Version of this run. A re-run of the same input creates a new version.
     */
    version: number;
    /**
     * True when the series had less history than the method requires. The run is recorded but the forecast values are omitted.
     */
    insufficient_history: boolean;
    created_at?: string;
    created_by?: string;
};

