/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $ForecastRunCreate = {
    description: `What to forecast, how, and for how long. The series is a metric of this deployment, not a cross tenant query.`,
    properties: {
        series: {
            description: `The metric to forecast.`,
            properties: {
                metric: {
                    type: 'string',
                    description: `Metric key, for example \`headcount\` or \`absence_rate\`.`,
                    isRequired: true,
                },
                filters: {
                    type: 'dictionary',
                    contains: {
                        properties: {
                        },
                    },
                },
                granularity: {
                    type: 'Enum',
                },
            },
            isRequired: true,
        },
        method: {
            type: 'Enum',
        },
        horizon: {
            type: 'number',
            description: `Number of periods to forecast.`,
            isRequired: true,
            minimum: 1,
        },
        backtest_window: {
            type: 'number',
            description: `Number of holdout periods used to measure the error.`,
            minimum: 1,
        },
        min_history_weeks: {
            type: 'number',
            description: `Minimum history the method needs. Below it the run is still created but is flagged \`insufficient_history\` and the forecast values are omitted.`,
            minimum: 1,
        },
    },
} as const;
