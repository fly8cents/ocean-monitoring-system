#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import deque
import numpy as np


class AnomalyDetector:
    def __init__(self, a1, b1, a2, b2, window=100, sigma=3.0):
        self.a1, self.b1 = a1, b1
        self.a2, self.b2 = a2, b2
        self.window = window
        self.sigma = sigma

        self.hum_res_hist = deque(maxlen=window)
        self.wt_res_hist = deque(maxlen=window)

    def update(self, temp, hum, wt):
        hum_res = hum - (self.a1 * temp + self.b1)
        wt_res = wt - (self.a2 * temp + self.b2)

        self.hum_res_hist.append(hum_res)
        self.wt_res_hist.append(wt_res)

        if len(self.hum_res_hist) < self.window:
            return {'ready': False, 'hum_alarm': False, 'wt_alarm': False}

        hum_slow = float(np.mean(self.hum_res_hist))
        wt_slow = float(np.mean(self.wt_res_hist))
        hum_fast = hum_res - hum_slow
        wt_fast = wt_res - wt_slow

        hum_std = float(np.std(self.hum_res_hist)) + 1e-9
        wt_std = float(np.std(self.wt_res_hist)) + 1e-9
        hum_th = self.sigma * hum_std
        wt_th = self.sigma * wt_std

        hum_alarm = abs(hum_fast) > hum_th
        wt_alarm = abs(wt_fast) > wt_th

        return {
            'ready': True,
            'hum_alarm': hum_alarm,
            'wt_alarm': wt_alarm,
            'hum_res': round(hum_res, 4),
            'wt_res': round(wt_res, 4),
            'hum_fast': round(hum_fast, 4),
            'wt_fast': round(wt_fast, 4),
            'hum_th': round(hum_th, 4),
            'wt_th': round(wt_th, 4),
        }
