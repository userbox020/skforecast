# Unit test backtesting_sarimax
# ==============================================================================
import re
import pytest
from pytest import approx
import numpy as np
import pandas as pd
from skforecast.ForecasterSarimax import ForecasterSarimax
from skforecast.model_selection_sarimax import backtesting_sarimax
from pmdarima.arima import ARIMA

# Fixtures
from ...ForecasterSarimax.tests.fixtures_ForecasterSarimax import y_datetime
from ...ForecasterSarimax.tests.fixtures_ForecasterSarimax import exog_datetime


def test_backtesting_sarimax_ValueError_when_initial_train_size_is_None():
    """
    Test ValueError is raised in backtesting_sarimax when initial_train_size is None.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(1,1,1)))

    initial_train_size = None
    
    err_msg = re.escape('`initial_train_size` must be an int smaller than the length of `y`.')
    with pytest.raises(ValueError, match = err_msg):
        backtesting_sarimax(
            forecaster         = forecaster,
            y                  = y_datetime,
            steps              = 4,
            metric             = 'mean_absolute_error',
            initial_train_size = initial_train_size,
            refit              = False,
            fixed_train_size   = False,
            exog               = None,
            alpha              = None,
            interval           = None,
            verbose            = False
        )


@pytest.mark.parametrize("initial_train_size", 
                         [(len(y_datetime)), (len(y_datetime) + 1)], 
                         ids = lambda value : f'len: {value}' )
def test_backtesting_sarimax_ValueError_when_initial_train_size_more_than_or_equal_to_len_y(initial_train_size):
    """
    Test ValueError is raised in backtesting_sarimax when initial_train_size >= len(y).
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(1,1,1)))
    
    err_msg = re.escape('`initial_train_size` must be an int smaller than the length of `y`.')
    with pytest.raises(ValueError, match = err_msg):
        backtesting_sarimax(
            forecaster         = forecaster,
            y                  = y_datetime,
            steps              = 4,
            metric             = 'mean_absolute_error',
            initial_train_size = initial_train_size,
            refit              = False,
            fixed_train_size   = False,
            exog               = None,
            alpha              = None,
            interval           = None,
            verbose            = False
        )


def test_backtesting_sarimax_ValueError_when_initial_train_size_less_than_forecaster_window_size():
    """
    Test ValueError is raised in backtesting_sarimax when initial_train_size < forecaster.window_size.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(1,1,1)))

    initial_train_size = forecaster.window_size - 1
    
    err_msg = re.escape(
            (f"`initial_train_size` must be greater than "
             f"forecaster's window_size ({forecaster.window_size}).")
        )
    with pytest.raises(ValueError, match = err_msg):
        backtesting_sarimax(
            forecaster         = forecaster,
            y                  = y_datetime,
            steps              = 4,
            metric             = 'mean_absolute_error',
            initial_train_size = initial_train_size,
            refit              = False,
            fixed_train_size   = False,
            exog               = None,
            alpha              = None,
            interval           = None,
            verbose            = False
        )


def test_backtesting_sarimax_TypeError_when_refit_not_bool():
    """
    Test TypeError is raised in backtesting_sarimax when refit is not bool.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(1,1,1)))

    refit = 'not_bool'
    
    err_msg = re.escape( f'`refit` must be boolean: `True`, `False`.')
    with pytest.raises(TypeError, match = err_msg):
        backtesting_sarimax(
            forecaster         = forecaster,
            y                  = y_datetime,
            steps              = 4,
            metric             = 'mean_absolute_error',
            initial_train_size = 12,
            refit              = refit,
            fixed_train_size   = False,
            exog               = None,
            alpha              = None,
            interval           = None,
            verbose            = False
        )


def test_output_backtesting_sarimax_no_refit_no_exog_no_remainder_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    no refit, 12 observations to backtest, steps=3 (no remainder), metric='mean_squared_error'. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 3,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = False,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.10564120819988289
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.81448569, 
                           0.73818098, 0.71739124, 0.33699337, 0.34024219, 
                           0.39178913, 0.66499417, 0.54139334, 0.53432513]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_no_refit_no_exog_remainder_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    yes refit, 12 observations to backtest, steps=5 (remainder), metric='mean_squared_error'. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 5,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = False,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.10061680900744897
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.73039455, 0.69111006,
                           0.49744496, 0.37841947, 0.3619615 , 0.43815806, 0.44457422,
                           0.70144038, 0.61758017]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_no_exog_no_remainder_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    yes refit, 12 observations to backtest, steps=3 (no remainder), metric='mean_squared_error'. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 3,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.1245724897025159
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.82489505, 0.77191505,
                           0.73750377, 0.30807646, 0.27854996, 0.28835934, 0.51981128,
                           0.51690468, 0.51726221]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_no_exog_remainder_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    yes refit, 12 observations to backtest, steps=5 (remainder), metric='mean_squared_error'. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 5,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.09556639597015694
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.73039455, 0.69111006,
                           0.4814143 , 0.5014026 , 0.48131545, 0.47225091, 0.4734432 ,
                           0.78337242, 0.65285038]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_fixed_train_size_no_exog_no_remainder_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    yes refit, fixed_train_size yes, 12 observations to backtest, steps=3 (no remainder), 
    metric='mean_squared_error'. Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 3,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = True,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.08703290568510223
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.56816834, 0.60577745,
                           0.61543978, 0.2837735 , 0.4109889 , 0.34055892, 0.54244717,
                           0.35633378, 0.55692658]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_fixed_train_size_no_exog_remainder_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    yes refit, fixed_train_size yes, 12 observations to backtest, steps=5 (remainder), 
    metric='mean_squared_error'. Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 5,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = True,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.14972067408401932
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.73039455, 0.69111006,
                           0.31724739, 0.1889182 , 0.29580158, 0.18153829, 0.2240739 ,
                           0.69979474, 0.58754509]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_no_refit_yes_exog_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, yes exog, 
    no refit, 12 observations to backtest, steps=3 (no remainder), metric='mean_squared_error'. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        exog               = exog_datetime,
                                        steps              = 3,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = False,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.08971294363961381
    expected_values = np.array(
                          [0.65076021, 0.57703261, 0.66853316, 0.71762052, 0.71677803,
                           0.67251158, 0.34619317, 0.32344791, 0.4671051 , 0.65322324,
                           0.55053341, 0.52974663]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_yes_exog_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, yes exog, 
    yes refit, 12 observations to backtest, steps=3 (no remainder), metric='mean_squared_error'. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        exog               = exog_datetime,
                                        steps              = 3,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.10175644418425829
    expected_values = np.array(
                          [0.65076021, 0.57703261, 0.66853316, 0.73931314, 0.7417212 ,
                           0.68038136, 0.31180477, 0.25796641, 0.42197043, 0.58873725,
                           0.5420918 , 0.47705565]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_fixed_train_size_yes_exog_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, yes exog, 
    yes refit, fixed_train_size, 12 observations to backtest, steps=5 (remainder), 
    metric='mean_squared_error'. Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        exog               = exog_datetime,
                                        steps              = 5,
                                        metric             = 'mean_squared_error',
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = True,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = 0.14118208637664512
    expected_values = np.array(
                          [0.65076021, 0.57703261, 0.66853316, 0.61862291, 0.69124954,
                           0.27388102, 0.18841554, 0.2528896 , 0.20359422, 0.21329373,
                           0.74976044, 0.6389244 ]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def my_metric(y_true, y_pred): # pragma: no cover
    """
    Callable metric
    """
    metric = ((y_true - y_pred)/len(y_true)).mean()
    
    return metric


def test_output_backtesting_sarimax_no_refit_yes_exog_callable_metric_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, yes exog, 
    no refit, 12 observations to backtest, steps=3 (no remainder), callable metric. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        exog               = exog_datetime,
                                        steps              = 3,
                                        metric             = my_metric,
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = False,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = -0.001653247249527463
    expected_values = np.array(
                          [0.65076021, 0.57703261, 0.66853316, 0.71762052, 0.71677803,
                           0.67251158, 0.34619317, 0.32344791, 0.4671051 , 0.65322324,
                           0.55053341, 0.52974663]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_no_refit_no_exog_list_of_metrics_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, yes exog, 
    no refit, 12 observations to backtest, steps=3 (no remainder), list of metrics. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 3,
                                        metric             = [my_metric, 'mean_absolute_error'],
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = False,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = [-0.0024305433379636946, 0.25015256206055664]
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.81448569, 0.73818098,
                           0.71739124, 0.33699337, 0.34024219, 0.39178913, 0.66499417,
                           0.54139334, 0.53432513]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_no_exog_callable_metric_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, no exog, 
    yes refit, 12 observations to backtest, steps=3 (no remainder), callable metric. 
    Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        steps              = 3,
                                        metric             = my_metric,
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = False,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = -0.00023250555300558177
    expected_values = np.array(
                          [0.63793971, 0.55322609, 0.71445518, 0.82489505, 0.77191505,
                           0.73750377, 0.30807646, 0.27854996, 0.28835934, 0.51981128,
                           0.51690468, 0.51726221]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


def test_output_backtesting_sarimax_yes_refit_fixed_train_size_yes_exog_list_of_metrics_with_mocked():
    """
    Test output of backtesting_sarimax with backtesting mocked, Series y is mocked, yes exog, 
    yes refit, fixed_train_size, 12 observations to backtest, steps=3 (no remainder), 
    list of metrics. Mocked done with skforecast 0.7.0.
    """
    forecaster = ForecasterSarimax(regressor=ARIMA(order=(2,2,2)))

    metric, backtest_predictions = backtesting_sarimax(
                                        forecaster         = forecaster,
                                        y                  = y_datetime,
                                        exog               = exog_datetime,
                                        steps              = 3,
                                        metric             = [my_metric, 'mean_absolute_error'],
                                        initial_train_size = len(y_datetime)-12,
                                        fixed_train_size   = True,
                                        refit              = True,
                                        alpha              = None,
                                        interval           = None,
                                        verbose            = False
                                   )
    
    expected_metric = [-0.00022025837526436814, 0.2716753720859064]
    expected_values = np.array(
                          [0.65076021, 0.57703261, 0.66853316, 0.76237117, 0.78537336,
                           0.74682351, 0.31979698, 0.32975211, 0.48280879, 0.48234909,
                           0.37537897, 0.48615521]
                      )

    expected_backtest_predictions = pd.DataFrame(
                                        data    = expected_values,
                                        columns = ['pred'],
                                        index   = pd.date_range(start='2038', periods=12, freq='A')
                                    )                                                     

    assert expected_metric == approx(metric)
    pd.testing.assert_frame_equal(expected_backtest_predictions, backtest_predictions)


# Falta el testing con intervalos