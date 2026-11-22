"""Baseline forecasters. Regressors predict the CHANGE s(t+h) - s(t); stage forecast = s(t) + change."""
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0)   # extended after a smoke run hit the old upper edge (100)
XGB_DEPTHS = (3, 5)


def persistence_change(n: int) -> np.ndarray:
    return np.zeros(n)


def trend_change(d_1h: np.ndarray, h_steps: int) -> np.ndarray:
    """Naive extrapolation of the last 1-hour rate of change over the horizon (Phase 1A definition)."""
    return d_1h * (h_steps * 0.25)


def trend_change_v2(d_w: np.ndarray, window_steps: int, h_steps: int, phi: float) -> np.ndarray:
    """Damped trend: phi x h(hours) x (change over window w / w hours)."""
    return phi * (h_steps * 0.25) * d_w / (window_steps * 0.25)


def fit_ridge(x, y, alpha, w=None):
    m = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    return m.fit(x, y, ridge__sample_weight=w) if w is not None else m.fit(x, y)


def _xgb_params(depth, seed):
    return dict(tree_method="hist", learning_rate=0.05, max_depth=depth, subsample=0.8, colsample_bytree=0.8,
                min_child_weight=5, n_jobs=-1, random_state=seed)


def fit_xgb(x, y, depth, x_val=None, y_val=None, n_estimators=600, seed=0, w=None):
    params = _xgb_params(depth, seed)
    if x_val is not None:
        m = xgb.XGBRegressor(n_estimators=n_estimators, early_stopping_rounds=50, eval_metric="rmse", objective="reg:squarederror", **params)
        m.fit(x, y, sample_weight=w, eval_set=[(x_val, y_val)], verbose=False)
        return m, int(m.best_iteration) + 1
    m = xgb.XGBRegressor(n_estimators=n_estimators, objective="reg:squarederror", **params)
    return m.fit(x, y, sample_weight=w), n_estimators


def fit_logit(x, y, c=0.1):
    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=300)).fit(x, y)


def fit_xgb_clf(x, y, depth=3, spw=1.0, x_val=None, y_val=None, n_estimators=400, seed=0):
    params = _xgb_params(depth, seed)
    params["scale_pos_weight"] = float(spw)
    if x_val is not None:
        m = xgb.XGBClassifier(n_estimators=n_estimators, early_stopping_rounds=40, eval_metric="logloss", **params)
        m.fit(x, y, eval_set=[(x_val, y_val)], verbose=False)
        return m, int(m.best_iteration) + 1
    m = xgb.XGBClassifier(n_estimators=n_estimators, **params)
    return m.fit(x, y), n_estimators


def rmse(a, b) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))
