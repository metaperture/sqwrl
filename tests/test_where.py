import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal


def assert_where_equals(df, where_df, tbl, where_tbl):
    #assert_series_equal(where_tbl.s, where_df)
    assert len(tbl[where_tbl]) == len(df[where_df]) == where_df.sum() # == where_tbl.sum()
    assert_frame_equal(tbl[where_tbl].df, df[where_df])

def test_inequalities(sampledf1, sampletbl1):
    tbl = sampletbl1
    df = sampledf1
    assert_where_equals(df, df["x"] < 3, tbl, tbl["x"] < 3)
    assert_where_equals(df, (df["x"] >= df["z"] * 2 * 2 / 3),
                        tbl, (tbl["x"] >= tbl["z"] * 2 * 2 / 3))
    assert_where_equals(df, df["x"] > df["z"],
                        tbl, tbl["x"] > tbl["z"])
    assert_where_equals(df, (df["x"] > 4) | (df["z"] >= 1.4),
                        tbl, (tbl["x"] > 4) | (tbl["z"] >= 1.4))

def test_membership(sampledf1, sampletbl1):
    tbl = sampletbl1
    df = sampledf1
    assert_where_equals(df, df["z"].isin(df["x"] / 2.0),
                        tbl, tbl["z"].isin(tbl["x"] / 2.0))
    assert_where_equals(df, df.index.isin(["c", "d"]),
                        tbl, tbl.index.isin(["c", "d"]))

def test_string(sampledf1, sampletbl1):
    tbl = sampletbl1
    df = sampledf1
    assert_where_equals(df, df.index.to_series().str.startswith("a"),
                        tbl, tbl.index.startswith("a"))

def test_null(sampledf1, sampletbl1):
    tbl = sampletbl1
    df = sampledf1
    assert_where_equals(df, pd.notnull(df["x"]),
                        tbl, tbl["x"] != None)
