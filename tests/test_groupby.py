import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

def test_groupby_agg(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2

    assert_series_equal(df2.groupby("y")["z"].sum(), tbl2.groupby("y")["z"].sum())
    assert_series_equal(df2.groupby("y")["z"].min(), tbl2.groupby("y")["z"].min())
    assert_series_equal(df2.groupby("y")["z"].max(), tbl2.groupby("y")["z"].max())
    assert_series_equal(df2.groupby("y")["z"].mean(), tbl2.groupby("y")["z"].mean())

    assert_frame_equal(df2.groupby("y").sum(), tbl2.groupby("y").sum())

    assert_series_equal(df2.groupby(["y", "w"])["z"].sum(), tbl2.groupby(["y", "w"])["z"].sum())
    assert_series_equal(df2.groupby(["y", "w"])["z"].min(), tbl2.groupby(["y", "w"])["z"].min())
    assert_series_equal(df2.groupby(["y", "w"])["z"].max(), tbl2.groupby(["y", "w"])["z"].max())
    assert_series_equal(df2.groupby(["y", "w"])["z"].mean(), tbl2.groupby(["y", "w"])["z"].mean())

    assert_series_equal(df2.groupby(["y", "w"], sort=True)["z"].sum(), tbl2.groupby(["y", "w"], sort=True)["z"].sum())
    assert_series_equal(df2.groupby(["y", "w"], sort=True)["z"].min(), tbl2.groupby(["y", "w"], sort=True)["z"].min())
    assert_series_equal(df2.groupby(["y", "w"], sort=True)["z"].max(), tbl2.groupby(["y", "w"], sort=True)["z"].max())
    assert_series_equal(df2.groupby(["y", "w"], sort=True)["z"].mean(), tbl2.groupby(["y", "w"], sort=True)["z"].mean())

    #assert_frame_equal(df2.groupby("y").aggregate(["sum", "mean", "std"]), tbl2.groupby("y").aggregate(["sum", "mean", "std"]))
    #assert_frame_equal(df2.groupby("y").agg({"z": "mean", "w": "sum"}), tbl2.groupby("y").aggregate({"z": "mean", "w": "sum"}))

def test_groupby_groups(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2

    assert_frame_equal(df2.groupby(["w"]).get_group("B"), tbl2.groupby(["w"]).get_group("B").df)
    #assert_series_equal(df2.groupby("y").size(), tbl2.groupby("y").size())

def test_groupby_series_groups(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2

    for (ix_df, s_df), (ix_tbl, s_tbl) in zip(df2["z"].groupby(df2["y"]), tbl2["z"].groupby(tbl2["y"])):
        assert ix_df == ix_tbl
        assert_series_equal(s_df, s_tbl.s)

def test_groupby_frame_groups(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2

    for (ix_df, df_df), (ix_tbl, df_tbl) in zip(df2.groupby("y"), tbl2.groupby("y")):
        assert ix_df == ix_tbl
        assert_frame_equal(df_df, df_tbl.df)
    
    for (ix_df, sel_df), (ix_tbl, sel_tbl) in zip(df2.groupby("w").groups.items(), tbl2.groupby("w").groups.items()):
        assert ix_df == ix_tbl
        assert_frame_equal(df2.loc[sel_df], tbl2[sel_tbl].df)
    
    for (ix_df, sel_df), (ix_tbl, sel_tbl) in zip(df2.groupby(["y", "z"]).groups.items(), tbl2.groupby(["y", "z"]).groups.items()):
        assert ix_df == ix_tbl
        assert_frame_equal(df2.loc[sel_df], tbl2[sel_tbl].df)

def test_groupby_intermediated(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2

    gb = df2.groupby(df2["y"], as_index=False)
    gb_sa = tbl2.groupby(tbl2["y"], as_index=False)
    assert_frame_equal(gb.sum(), gb_sa.sum())
    assert len(gb) == len(gb_sa)
    assert_frame_equal(gb.aggregate("mean"), gb_sa.aggregate("mean"))

def test_groupby_lazy_intermediated(sampledf2, sampletbl2):
    tbl2 = sampletbl2
    df2 = sampledf2

    gb = df2.groupby(df2["y"], as_index=False)
    gb_sa = tbl2.groupby(tbl2["y"], as_index=False)
    vt = gb_sa.agg("count", as_df=False)
    assert len(vt) == len(gb.agg("count"))
    assert_frame_equal(vt.df, gb.agg("count"))
    assert_series_equal((vt["w"] + vt["z"]).s, gb.agg("count")["w"] + gb.agg("count")["z"])

# TODO: gb transform...
# gb.transform(lambda x: x)
