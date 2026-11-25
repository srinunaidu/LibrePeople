/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ForecastRun = {
    description: `One forecast run, with everything needed to judge it: the method that was used, the window it was fitted on, the measured error on a holdout, the confidence band, and a hash of the input so the run can be reproduced.`,
    properties: {
        id: {
            type: 'string',
            isRequired: true,
        },
        series: {
            type: 'dictionary',
            contains: {
                properties: {
                },
            },
            isRequired: true,
        },
        method: {
            type: 'string',
            description: `The method that was actually used. Resolved when the request said \`auto\`.`,
            isRequired: true,
        },
        method_version: {
            type: 'string',
            description: `Version of the forecasting implementation that produced the result.`,
        },
        data_window: {
            description: `The observations the model was fitted on.`,
            properties: {
                start: {
                    type: 'string',
                    isRequired: true,
                    format: 'date',
                },
                end: {
                    type: 'string',
                    isRequired: true,
                    format: 'date',
                },
                observations: {
                    type: 'number',
                    isRequired: true,
                },
            },
        },
        backtest: {
            description: `The measured error on a holdout. \`mape\` is the mean absolute percentage error, \`mase\` the mean absolute scaled error.`,
            properties: {
                mape: {
                    type: 'number',
                    description: `Mean absolute percentage error over the holdout. Null when it cannot be computed.`,
                    isRequired: true,
                    isNullable: true,
                },
                mase: {
                    type: 'number',
                    description: `Mean absolute scaled error over the holdout. Null when it cannot be computed.`,
                    isRequired: true,
                    isNullable: true,
                },
                holdout_length: {
                    type: 'number',
                    description: `Number of periods held out of the fit.`,
                    isRequired: true,
                },
                holdout_start: {
                    type: 'string',
                    format: 'date',
                },
                holdout_end: {
                    type: 'string',
                    format: 'date',
                },
            },
        },
        confidence_band: {
            description: `The interval the forecast is stated with.`,
            properties: {
                level: {
                    type: 'number',
                    description: `Coverage of the interval, for example 0.8.`,
                },
                method: {
                    type: 'string',
                    description: `How the band was derived, for example \`residual_variance\`.`,
                },
            },
        },
        forecast: {
            type: 'array',
            contains: {
                properties: {
                    period: {
                        type: 'string',
                        isRequired: true,
                        format: 'date',
                    },
                    value: {
                        type: 'number',
                        isRequired: true,
                    },
                    lower: {
                        type: 'number',
                    },
                    upper: {
                        type: 'number',
                    },
                },
            },
        },
        input_hash: {
            type: 'string',
            description: `Hash of the exact input the run was computed from. The same input hash means the same run.`,
            isRequired: true,
        },
        version: {
            type: 'number',
            description: `Version of this run. A re-run of the same input creates a new version.`,
            isRequired: true,
            minimum: 1,
        },
        insufficient_history: {
            type: 'boolean',
            description: `True when the series had less history than the method requires. The run is recorded but the forecast values are omitted.`,
            isRequired: true,
        },
        created_at: {
            type: 'string',
            format: 'date-time',
        },
        created_by: {
            type: 'string',
        },
    },
} as const;
