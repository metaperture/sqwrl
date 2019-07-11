import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

def test_insert(sampledf1, memdb):
    assert list(memdb) == []
    assert len(memdb) == 0
    memdb["test"] = sampledf1
    assert list(memdb) == ["test"]
    assert len(memdb) == 1

def test_basic_equivalence(sampledf1, sampletbl1):
    assert len(sampletbl1) == len(sampledf1)
    assert_frame_equal(sampletbl1.df, sampledf1)
    assert_series_equal(sampletbl1.dtypes, sampledf1.dtypes)
    assert_frame_equal(sampletbl1.head(3).df, sampledf1.head(3))
    for col in sampledf1.columns:
        assert_series_equal(sampledf1[col], sampletbl1[col].s)
        assert sampledf1[col].dtype == sampletbl1[col].dtype
        assert_series_equal(sampledf1[col].head(3), sampletbl1[col].head(3).s)

def test_sorting(sampledf1, sampletbl1):
    assert_frame_equal(sampletbl1.sort_index(ascending=False).df, sampledf1.sort_index(ascending=False))
    assert_frame_equal(sampletbl1.sort_values(["z", "x"]).df, sampledf1.sort_values(["z", "x"]))
    assert_frame_equal(sampletbl1.sort_values(["x", "z"]).df, sampledf1.sort_values(["x", "z"]))
    assert_frame_equal(sampletbl1.sort_values("z")[:3].df, sampledf1.sort_values("z")[:3])
    assert_frame_equal(sampletbl1.sort_index(ascending=False).df, sampledf1.sort_index(ascending=False))
    assert_frame_equal(sampletbl1.sort_index(ascending=True).df, sampledf1.sort_index(ascending=True))

    #df_tmp = sampledf1.assign(tmp=sampledf1["z"] - sampledf1["x"])
    #assert_frame_equal(df_tmp.sort_values("tmp").drop("tmp"),
    #                   sampletbl1.sort_values(sampletbl1["z"] - sampletbl1["x"]).df)

def test_loc(sampledf1, sampletbl1):
    assert_series_equal(sampletbl1["x"].loc[["a", "d"]], sampledf1["x"].loc[["a", "d"]])
    assert_frame_equal(sampletbl1[["z", "x"]].iloc[1:-2].df, sampledf1[["z", "x"]].iloc[1:-2])
    assert_series_equal(sampletbl1.loc["a"], sampledf1.loc["a"])
    assert_frame_equal(sampletbl1.loc[["a", "c"]], sampledf1.loc[["a", "c"]])
    assert_series_equal(sampletbl1["x"].head(2).s, sampledf1["x"].head(2))

def test_indexing(sampledf1, sampletbl1):
    assert_series_equal(sampletbl1.set_index("x", append=True)["z"].s, sampledf1.set_index("x", append=True)["z"])
    df2 = sampledf1.copy()
    tbl2 = sampletbl1.copy()
    tbl2.index.name = "ix"
    df2.index.name = "ix"
    #assert_frame_equal(tbl2.df, df2)
    #tbl.set_index("x", drop=False).df
    #tbl.set_index("x", append=True).df
    #tbl2.set_index("x", append=True).df
    #tbl.set_index("x", append=True)["z"].s
    #tbl2.reset_index()["ix"].s
