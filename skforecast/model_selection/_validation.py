################################################################################
#                          skforecast._validation                              #
#                                                                              #
# This work by skforecast team is licensed under the BSD 3-Clause License.     #
################################################################################
# coding=utf-8

from copy import deepcopy
from typing import Union, Tuple, Optional, Callable
import warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed, cpu_count
from tqdm.auto import tqdm
from ..model_selection._split import TimeSeriesFold
from ..metrics import add_y_train_argument, _get_metric
from ..exceptions import LongTrainingWarning, IgnoredArgumentWarning
from ..utils import (
    check_backtesting_input,
    select_n_jobs_backtesting
)


def _backtesting_forecaster(
    forecaster: object,
    y: pd.Series,
    metric: Union[str, Callable, list],
    cv: TimeSeriesFold,
    exog: Optional[Union[pd.Series, pd.DataFrame]] = None,
    interval: Optional[list] = None,
    n_boot: int = 250,
    random_state: int = 123,
    use_in_sample_residuals: bool = True,
    use_binned_residuals: bool = False,
    n_jobs: Union[int, str] = 'auto',
    verbose: bool = False,
    show_progress: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Backtesting of forecaster model following the folds generated by the TimeSeriesFold
    class and using the metric(s) provided.

    If `forecaster` is already trained and `initial_train_size` is set to `None` in the
    TimeSeriesFold class, no initial train will be done and all data will be used
    to evaluate the model. However, the first `len(forecaster.last_window)` observations
    are needed to create the initial predictors, so no predictions are calculated for
    them.
    
    A copy of the original forecaster is created so that it is not modified during the
    process.
    
    Parameters
    ----------
    forecaster : ForecasterAutoreg, ForecasterAutoregDirect
        Forecaster model.
    y : pandas Series
        Training time series.
    metric : str, Callable, list
        Metric used to quantify the goodness of fit of the model.
        
        - If `string`: {'mean_squared_error', 'mean_absolute_error',
        'mean_absolute_percentage_error', 'mean_squared_log_error',
        'mean_absolute_scaled_error', 'root_mean_squared_scaled_error'}
        - If `Callable`: Function with arguments `y_true`, `y_pred` and `y_train`
        (Optional) that returns a float.
        - If `list`: List containing multiple strings and/or Callables.
    cv : TimeSeriesFold
        TimeSeriesFold object with the information needed to split the data into folds.
        **New in version 0.14.0**
    exog : pandas Series, pandas DataFrame, default `None`
        Exogenous variable/s included as predictor/s. Must have the same
        number of observations as `y` and should be aligned so that y[i] is
        regressed on exog[i].
    interval : list, default `None`
        Confidence of the prediction interval estimated. Sequence of percentiles
        to compute, which must be between 0 and 100 inclusive. For example, 
        interval of 95% should be as `interval = [2.5, 97.5]`. If `None`, no
        intervals are estimated.
    n_boot : int, default `500`
        Number of bootstrapping iterations used to estimate prediction
        intervals.
    random_state : int, default `123`
        Sets a seed to the random generator, so that boot intervals are always 
        deterministic.
    use_in_sample_residuals : bool, default `True`
        If `True`, residuals from the training data are used as proxy of prediction 
        error to create prediction intervals. If `False`, out_sample_residuals 
        are used if they are already stored inside the forecaster.
    use_binned_residuals : bool, default `False`
        If `True`, residuals used in each bootstrapping iteration are selected
        conditioning on the predicted values. If `False`, residuals are selected
        randomly without conditioning on the predicted values.
    n_jobs : int, 'auto', default `'auto'`
        The number of jobs to run in parallel. If `-1`, then the number of jobs is 
        set to the number of cores. If 'auto', `n_jobs` is set using the function
        skforecast.utils.select_n_jobs_backtesting.
    verbose : bool, default `False`
        Print number of folds and index of training and validation sets used 
        for backtesting.
    show_progress : bool, default `True`
        Whether to show a progress bar.

    Returns
    -------
    metric_values : pandas DataFrame
        Value(s) of the metric(s).
    backtest_predictions : pandas DataFrame
        Value of predictions and their estimated interval if `interval` is not `None`.

        - column pred: predictions.
        - column lower_bound: lower bound of the interval.
        - column upper_bound: upper bound of the interval.
    
    """

    forecaster = deepcopy(forecaster)
    cv = deepcopy(cv)

    cv.set_params({
        'window_size': forecaster.window_size,
        'differentiation': forecaster.differentiation,
        'return_all_indexes': False,
        'verbose': verbose
    })

    window_size = cv.window_size
    initial_train_size = cv.initial_train_size
    refit = cv.refit
    gap = cv.gap
    
    if n_jobs == 'auto':
        n_jobs = select_n_jobs_backtesting(
                     forecaster = forecaster,
                     refit      = refit
                 )
    elif not isinstance(refit, bool) and refit != 1 and n_jobs != 1:
        warnings.warn(
            ("If `refit` is an integer other than 1 (intermittent refit). `n_jobs` "
             "is set to 1 to avoid unexpected results during parallelization."),
             IgnoredArgumentWarning
        )
        n_jobs = 1
    else:
        n_jobs = n_jobs if n_jobs > 0 else cpu_count()

    if not isinstance(metric, list):
        metrics = [
            _get_metric(metric=metric)
            if isinstance(metric, str)
            else add_y_train_argument(metric)
        ]
    else:
        metrics = [
            _get_metric(metric=m)
            if isinstance(m, str)
            else add_y_train_argument(m) 
            for m in metric
        ]

    store_in_sample_residuals = False if interval is None else True

    folds = cv.split(X=y, as_pandas=False)

    if initial_train_size is not None:
        # First model training, this is done to allow parallelization when `refit`
        # is `False`. The initial Forecaster fit is outside the auxiliary function.
        exog_train = exog.iloc[:initial_train_size, ] if exog is not None else None
        forecaster.fit(
            y                         = y.iloc[:initial_train_size, ],
            exog                      = exog_train,
            store_in_sample_residuals = store_in_sample_residuals
        )
        # This is done to allow parallelization when `refit` is `False`. The initial 
        # Forecaster fit is outside the auxiliary function.
        folds[0][4] = False

    if refit:
        n_of_fits = int(len(folds) / refit)
        if type(forecaster).__name__ != 'ForecasterAutoregDirect' and n_of_fits > 50:
            warnings.warn(
                (f"The forecaster will be fit {n_of_fits} times. This can take substantial"
                 f" amounts of time. If not feasible, try with `refit = False`.\n"),
                LongTrainingWarning
            )
        elif type(forecaster).__name__ == 'ForecasterAutoregDirect' and n_of_fits * forecaster.steps > 50:
            warnings.warn(
                (f"The forecaster will be fit {n_of_fits * forecaster.steps} times "
                 f"({n_of_fits} folds * {forecaster.steps} regressors). This can take "
                 f"substantial amounts of time. If not feasible, try with `refit = False`.\n"),
                LongTrainingWarning
            )

    if show_progress:
        folds = tqdm(folds)

    def _fit_predict_forecaster(y, exog, forecaster, interval, fold, gap):
        """
        Fit the forecaster and predict `steps` ahead. This is an auxiliary 
        function used to parallelize the backtesting_forecaster function.
        """

        train_iloc_start       = fold[0][0]
        train_iloc_end         = fold[0][1]
        last_window_iloc_start = fold[1][0]
        last_window_iloc_end   = fold[1][1]
        test_iloc_start        = fold[2][0]
        test_iloc_end          = fold[2][1]

        if fold[4] is False:
            # When the model is not fitted, last_window must be updated to include
            # the data needed to make predictions.
            last_window_y = y.iloc[last_window_iloc_start:last_window_iloc_end]
        else:
            # The model is fitted before making predictions. If `fixed_train_size`
            # the train size doesn't increase but moves by `steps` in each iteration.
            # If `False` the train size increases by `steps` in each iteration.
            y_train = y.iloc[train_iloc_start:train_iloc_end, ]
            exog_train = (
                exog.iloc[train_iloc_start:train_iloc_end,] if exog is not None else None
            )
            last_window_y = None
            forecaster.fit(
                y                         = y_train, 
                exog                      = exog_train, 
                store_in_sample_residuals = store_in_sample_residuals
            )

        next_window_exog = exog.iloc[test_iloc_start:test_iloc_end, ] if exog is not None else None

        steps = len(range(test_iloc_start, test_iloc_end))
        if type(forecaster).__name__ == 'ForecasterAutoregDirect' and gap > 0:
            # Select only the steps that need to be predicted if gap > 0
            test_no_gap_iloc_start = fold[3][0]
            test_no_gap_iloc_end   = fold[3][1]
            steps = list(
                np.arange(len(range(test_no_gap_iloc_start, test_no_gap_iloc_end)))
                + gap
                + 1
            )

        if interval is None:
            pred = forecaster.predict(
                       steps       = steps,
                       last_window = last_window_y,
                       exog        = next_window_exog
                   )
        else:
            pred = forecaster.predict_interval(
                       steps                   = steps,
                       last_window             = last_window_y,
                       exog                    = next_window_exog,
                       interval                = interval,
                       n_boot                  = n_boot,
                       random_state            = random_state,
                       use_in_sample_residuals = use_in_sample_residuals,
                       use_binned_residuals    = use_binned_residuals,
                   )

        if type(forecaster).__name__ != 'ForecasterAutoregDirect' and gap > 0:
            pred = pred.iloc[gap:, ]

        return pred

    backtest_predictions = (
        Parallel(n_jobs=n_jobs)
        (delayed(_fit_predict_forecaster)
        (y=y, exog=exog, forecaster=forecaster, interval=interval, fold=fold, gap=gap)
         for fold in folds)
    )

    backtest_predictions = pd.concat(backtest_predictions)
    if isinstance(backtest_predictions, pd.Series):
        backtest_predictions = pd.DataFrame(backtest_predictions)

    train_indexes = []
    for i, fold in enumerate(folds):
        fit_fold = fold[-1]
        if i == 0 or fit_fold:
            train_iloc_start = fold[0][0] + window_size  # Exclude observations used to create predictors
            train_iloc_end = fold[0][1]
            train_indexes.append(np.arange(train_iloc_start, train_iloc_end))
    
    train_indexes = np.unique(np.concatenate(train_indexes))
    y_train = y.iloc[train_indexes]

    metric_values = [
        m(
            y_true = y.loc[backtest_predictions.index],
            y_pred = backtest_predictions['pred'],
            y_train = y_train
        ) 
        for m in metrics
    ]

    metric_values = pd.DataFrame(
        data    = [metric_values],
        columns = [m.__name__ for m in metrics]
    )
    
    return metric_values, backtest_predictions


def backtesting_forecaster(
    forecaster: object,
    y: pd.Series,
    cv: TimeSeriesFold,
    metric: Union[str, Callable, list],
    exog: Optional[Union[pd.Series, pd.DataFrame]] = None,
    interval: Optional[list] = None,
    n_boot: int = 250,
    random_state: int = 123,
    use_in_sample_residuals: bool = True,
    use_binned_residuals: bool = False,
    n_jobs: Union[int, str] = 'auto',
    verbose: bool = False,
    show_progress: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Backtesting of forecaster model following the folds generated by the TimeSeriesFold
    class and using the metric(s) provided.

    If `forecaster` is already trained and `initial_train_size` is set to `None` in the
    TimeSeriesFold class, no initial train will be done and all data will be used
    to evaluate the model. However, the first `len(forecaster.last_window)` observations
    are needed to create the initial predictors, so no predictions are calculated for
    them.
    
    A copy of the original forecaster is created so that it is not modified during 
    the process.

    Parameters
    ----------
    forecaster : ForecasterAutoreg, ForecasterAutoregDirect
        Forecaster model.
    y : pandas Series
        Training time series.
    cv : TimeSeriesFold
        TimeSeriesFold object with the information needed to split the data into folds.
        **New in version 0.14.0**
    metric : str, Callable, list
        Metric used to quantify the goodness of fit of the model.
        
        - If `string`: {'mean_squared_error', 'mean_absolute_error',
        'mean_absolute_percentage_error', 'mean_squared_log_error',
        'mean_absolute_scaled_error', 'root_mean_squared_scaled_error'}
        - If `Callable`: Function with arguments `y_true`, `y_pred` and `y_train`
        (Optional) that returns a float.
        - If `list`: List containing multiple strings and/or Callables.
    exog : pandas Series, pandas DataFrame, default `None`
        Exogenous variable/s included as predictor/s. Must have the same
        number of observations as `y` and should be aligned so that y[i] is
        regressed on exog[i].
    interval : list, default `None`
        Confidence of the prediction interval estimated. Sequence of percentiles
        to compute, which must be between 0 and 100 inclusive. For example, 
        interval of 95% should be as `interval = [2.5, 97.5]`. If `None`, no
        intervals are estimated.
    n_boot : int, default `500`
        Number of bootstrapping iterations used to estimate prediction
        intervals.
    random_state : int, default `123`
        Sets a seed to the random generator, so that boot intervals are always 
        deterministic.
    use_in_sample_residuals : bool, default `True`
        If `True`, residuals from the training data are used as proxy of prediction 
        error to create prediction intervals. If `False`, out_sample_residuals 
        are used if they are already stored inside the forecaster.
    use_binned_residuals : bool, default `False`
        If `True`, residuals used in each bootstrapping iteration are selected
        conditioning on the predicted values. If `False`, residuals are selected
        randomly without conditioning on the predicted values.
    n_jobs : int, 'auto', default `'auto'`
        The number of jobs to run in parallel. If `-1`, then the number of jobs is 
        set to the number of cores. If 'auto', `n_jobs` is set using the function
        skforecast.utils.select_n_jobs_backtesting.
    verbose : bool, default `False`
        Print number of folds and index of training and validation sets used 
        for backtesting.
    show_progress : bool, default `True`
        Whether to show a progress bar.

    Returns
    -------
    metric_values : pandas DataFrame
        Value(s) of the metric(s).
    backtest_predictions : pandas DataFrame
        Value of predictions and their estimated interval if `interval` is not `None`.

        - column pred: predictions.
        - column lower_bound: lower bound of the interval.
        - column upper_bound: upper bound of the interval.
    
    """

    forecaters_allowed = [
        'ForecasterAutoreg', 
        'ForecasterAutoregDirect',
        'ForecasterEquivalentDate'
    ]
    
    if type(forecaster).__name__ not in forecaters_allowed:
        raise TypeError(
            (f"`forecaster` must be of type {forecaters_allowed}, for all other types of "
             f" forecasters use the functions available in the other `model_selection` "
             f"modules.")
        )
    
    check_backtesting_input(
        forecaster              = forecaster,
        cv                      = cv,
        y                       = y,
        metric                  = metric,
        interval                = interval,
        n_boot                  = n_boot,
        random_state            = random_state,
        use_in_sample_residuals = use_in_sample_residuals,
        use_binned_residuals    = use_binned_residuals,
        n_jobs                  = n_jobs,
        show_progress           = show_progress
    )
    
    if type(forecaster).__name__ == 'ForecasterAutoregDirect' and \
       forecaster.steps < cv.steps + cv.gap:
        raise ValueError(
            (f"When using a ForecasterAutoregDirect, the combination of steps "
             f"+ gap ({cv.steps + cv.gap}) cannot be greater than the `steps` parameter "
             f"declared when the forecaster is initialized ({forecaster.steps}).")
        )
    
    metric_values, backtest_predictions = _backtesting_forecaster(
        forecaster              = forecaster,
        y                       = y,
        cv                      = cv,
        metric                  = metric,
        exog                    = exog,
        interval                = interval,
        n_boot                  = n_boot,
        random_state            = random_state,
        use_in_sample_residuals = use_in_sample_residuals,
        use_binned_residuals    = use_binned_residuals,
        n_jobs                  = n_jobs,
        verbose                 = verbose,
        show_progress           = show_progress
    )

    return metric_values, backtest_predictions
