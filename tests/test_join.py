import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

def test_join1(sampledf1, sampletbl1, sampledf2, sampletbl2):
    tbl = sampletbl1
    df = sampledf1
    tbl2 = sampletbl2
    df2 = sampledf2
    return
    assert_frame_equal(tbl.reset_index().join(tbl2, on="y", lsuffix="l").df,
                       df.reset_index().join(df2, on="y", lsuffix="l"))
    
def test_join2(sampledf1, sampletbl1, sampledf2, sampletbl2):
    tbl = sampletbl1
    df = sampledf1
    tbl2 = sampletbl2
    df2 = sampledf2
    return
    assert_frame_equal(tbl.join(tbl2.set_index("y"), how="right", lsuffix="l").df,
                       df.join(df2.set_index("y"), how="right", lsuffix="l"))

def test_join3(sampledf1, sampletbl1, sampledf2, sampletbl2):
    tbl = sampletbl1
    df = sampledf1
    tbl2 = sampletbl2
    df2 = sampledf2
    return
    assert_frame_equal(tbl.join(tbl2.set_index("y"), lsuffix="l").df,
                       df.join(df2.set_index("y"), lsuffix="l"))

def test_join4(sampledf1, sampletbl1, sampledf2, sampletbl2):
    tbl = sampletbl1
    df = sampledf1
    tbl2 = sampletbl2
    df2 = sampledf2
    return
    assert_frame_equal(tbl.join(tbl, lsuffix="l", rsuffix="r").df,
                       df.join(df, lsuffix="l", rsuffix="r"))
