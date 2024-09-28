# Unit test fit ForecasterAutoregDirect
# ==============================================================================
import re
import pytest
import numpy as np
import pandas as pd
from skforecast.ForecasterAutoregDirect import ForecasterAutoregDirect
from sklearn.linear_model import LinearRegression

# Fixtures
from .fixtures_ForecasterAutoregDirect import y
from .fixtures_ForecasterAutoregDirect import exog


def test_forecaster_y_exog_features_stored():
    """
    Test forecaster stores y and exog features after fitting.
    """
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2)
    forecaster.fit(y=y, exog=exog)

    exog_in_ = True
    exog_type_in_ = type(exog)
    exog_names_in_ = ['exog']
    exog_dtypes_in_ = {'exog': exog.dtype}
    X_train_exog_names_out_ = ['exog']
    X_train_direct_exog_names_out_ = ['exog_step_1', 'exog_step_2']
    X_train_features_names_out_ = ['lag_1', 'lag_2', 'lag_3', 'exog_step_1', 'exog_step_2']
    
    assert forecaster.exog_in_ == exog_in_
    assert forecaster.exog_type_in_ == exog_type_in_
    assert forecaster.exog_names_in_ == exog_names_in_
    assert forecaster.exog_dtypes_in_ == exog_dtypes_in_
    assert forecaster.X_train_exog_names_out_ == X_train_exog_names_out_
    assert forecaster.X_train_direct_exog_names_out_ == X_train_direct_exog_names_out_
    assert forecaster.X_train_features_names_out_ == X_train_features_names_out_


def test_forecaster_DatetimeIndex_index_freq_stored():
    """
    Test serie_with_DatetimeIndex.index.freqstr is stored in forecaster.index_freq_.
    """
    serie_with_DatetimeIndex = pd.Series(
        data  = np.arange(10),
        index = pd.date_range(start='2022-01-01', periods=10)
    )
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2)
    forecaster.fit(y=serie_with_DatetimeIndex)
    expected = serie_with_DatetimeIndex.index.freqstr
    results = forecaster.index_freq_

    assert results == expected


def test_forecaster_index_step_stored():
    """
    Test serie without DatetimeIndex, step is stored in forecaster.index_freq_.
    """
    y = pd.Series(data=np.arange(10))
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2)
    forecaster.fit(y=y)
    expected = y.index.step
    results = forecaster.index_freq_

    assert results == expected
    

@pytest.mark.parametrize("n_jobs", [1, -1, 'auto'], 
                         ids=lambda n_jobs: f'n_jobs: {n_jobs}')
def test_fit_in_sample_residuals_stored(n_jobs):
    """
    Test that values of in_sample_residuals_ are stored after fitting.
    """
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2, n_jobs=n_jobs)
    forecaster.fit(y=pd.Series(np.arange(5)))
    expected = {1: np.array([0.]),
                2: np.array([0.])}
    results = forecaster.in_sample_residuals_

    assert isinstance(results, dict)
    assert all(isinstance(x, np.ndarray) for x in results.values())
    assert results.keys() == expected.keys()
    assert all(all(np.isclose(results[k], expected[k])) for k in expected.keys())


@pytest.mark.parametrize("n_jobs", [1, -1, 'auto'], 
                         ids=lambda n_jobs: f'n_jobs: {n_jobs}')
def test_fit_same_residuals_when_residuals_greater_than_1000(n_jobs):
    """
    Test fit return same residuals when residuals len is greater than 1000.
    Testing with two different forecaster.
    """
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2, n_jobs=n_jobs)
    forecaster.fit(y=pd.Series(np.arange(1200)))
    results_1 = forecaster.in_sample_residuals_

    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2, n_jobs=n_jobs)
    forecaster.fit(y=pd.Series(np.arange(1200)))
    results_2 = forecaster.in_sample_residuals_

    assert isinstance(results_1, dict)
    assert all(isinstance(x, np.ndarray) for x in results_1.values())
    assert isinstance(results_2, dict)
    assert all(isinstance(x, np.ndarray) for x in results_2.values())
    assert results_1.keys() == results_2.keys()
    assert all(len(results_1[k] == 1000) for k in results_1.keys())
    assert all(len(results_2[k] == 1000) for k in results_2.keys())
    assert all(all(results_1[k] == results_2[k]) for k in results_2.keys())


@pytest.mark.parametrize("n_jobs", [1, -1, 'auto'], 
                         ids=lambda n_jobs: f'n_jobs: {n_jobs}')
def test_fit_in_sample_residuals_not_stored(n_jobs):
    """
    Test that values of in_sample_residuals_ are not stored after fitting
    when `store_in_sample_residuals=False`.
    """
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2, n_jobs=n_jobs)
    forecaster.fit(y=pd.Series(np.arange(5)), store_in_sample_residuals=False)
    expected = {1: None, 2: None}
    results = forecaster.in_sample_residuals_

    assert isinstance(results, dict)
    assert results.keys() == expected.keys()
    assert all(results[k] == expected[k] for k in expected.keys())


@pytest.mark.parametrize("store_last_window", 
                         [True, False], 
                         ids=lambda lw: f'store_last_window: {lw}')
def test_fit_last_window_stored(store_last_window):
    """
    Test that values of last window are stored after fitting.
    """
    y = pd.Series(np.arange(20), name='y')
    forecaster = ForecasterAutoregDirect(LinearRegression(), lags=3, steps=2)
    forecaster.fit(y=y, store_last_window=store_last_window)

    expected = pd.Series(
        np.array([17, 18, 19]), index=[17, 18, 19]
    ).to_frame(name='y')

    if store_last_window:
        pd.testing.assert_frame_equal(forecaster.last_window_, expected)
    else:
        assert forecaster.last_window_ is None
