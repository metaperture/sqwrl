import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

def test_series_agg(sampledf1, sampletbl1):
    tbl = sampletbl1
    df = sampledf1
    assert_series_equal(tbl.max(), df.max())
    assert_series_equal(tbl[tbl["z"] > 1.4].mean(), df[df["z"] > 1.4].mean())
    #assert_series_equal((tbl.max(axis=1) - tbl.min(axis=1)).s, df.max(axis=1) - df.min(axis=1))
    assert tbl[tbl["x"] >= tbl["x"].mean()]["x"].min() == df[df["x"] >= df["x"].mean()]["x"].min()
    assert_series_equal(tbl.nunique(), df.nunique())
    assert tbl[tbl["x"] < tbl["x"].mean()]["x"].nunique() == df[df["x"] < df["x"].mean()]["x"].nunique()
    assert tbl.index.max() == df.index.max()
    assert_series_equal(tbl.max(axis=0), df.max(axis=0))

def test_series_agg(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2
    #assert_series_equal(tbl2.sort_values("y")["y"].distinct().s, df2.sort_values("y")["y"].distinct())
    #assert_series_equal(tbl2.sort_values(tbl2["y"])["y"].distinct().s, df2.sort_values(df2["y"])["y"].distinct())
