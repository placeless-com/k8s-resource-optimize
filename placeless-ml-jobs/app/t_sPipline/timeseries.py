import pandas as pd
import time
import numpy as np
from datetime import datetime
from datetime import timedelta
from statsmodels.tsa.stattools import acf, pacf
from statsmodels.tsa.arima_model import ARMA,ARIMA
from time import time
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.statespace.sarimax import SARIMAX
# from statsmodels.tsa.seasonal import STL
from pmdarima import auto_arima, arima

from pmdarima import pipeline
from pmdarima import model_selection
from pmdarima import preprocessing as ppc
import copy
class TSP():
    def __init__(self, seasonal=False,seasonal_period=0):
        self.__model = None
        self.seasonal = seasonal
        self.seasonal_period = seasonal_period

    @property
    def model(self):
        return self.__model

    def adf_test(self, data_train: list):
        """
        :param data: memory or cpu Series
        :return: bool -> True for stationary an False for not
        """
        adf = adfuller(data_train)
        p_val = adf[1]
        if p_val <= 0.05:
            return True
        else:
            return False

    def make_stationary(self,data):
        data = copy.deepcopy(data)
        diff_data = data.diff(1)[1:]
        num_of_diff = 1

        while not self.adf_test(diff_data) and num_of_diff < 4:
            diff_data = diff_data.diff(1)[1:]
            num_of_diff += 1
        return num_of_diff

    def process_pipline(self, data_train):
        model = pipeline.Pipeline([
                    ("arima", arima.AutoARIMA())])

        self.__model = model

    def model_selection(self, data_train):
         stationary = self.adf_test(data_train)
         default_d = 1
         if stationary:
             default_d -= 1
         else:
              default_d = self.make_stationary(data_train)

         if self.seasonal:
             model_pipe = pipeline.Pipeline([
                 ("arima", arima.AutoARIMA(d=default_d, seasonal=True, stepwise=True, m=self.seasonal_period,
                                           random_state=20, n_fits=20, error_action='ignore'))])
         else:
             model_pipe = pipeline.Pipeline([
                 ("arima",  arima.AutoARIMA(d=default_d, seasonal=False, stepwise=True,
                                      random_state=20, n_fits=20, error_action='ignore'))])

    def get_model(self):
        return copy.deepcopy(self.__model)

    def update_pipline(self, new_data):
        start_time = time.time()
        self.__model.update(new_data)
        end_time = time.time() - start_time

    def fit_data(self, train_data):
        self.__model.fit(train_data)

    def get_prediction(self, lags=1, conf_int=False):
        """
        :return: the predictions and the confidence intervals
        """
        return self.__model.predict(n_periods=lags, return_conf_int=conf_int)











