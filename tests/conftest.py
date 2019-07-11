import pytest
import pandas as pd
from sqwrl import DB

@pytest.fixture
def memdb():
    return DB('sqlite:///:memory:')

@pytest.fixture
def sampledf1():
    return pd.DataFrame({"x": [1,2,3,4,5], "y": list("abcdf"), "z": [1.0, 1.5, 1.5, 1.2, 1.3]}).set_index("y")

@pytest.fixture
def sampletbl1(memdb, sampledf1):
    memdb["test1"] = sampledf1
    return memdb["test1"]

@pytest.fixture
def sampledf2():
    return pd.DataFrame({"x": [1,2,3,4,5], "y": list("aaccg"), "z": [1.0, 1.5, 1.5, 1.2, 1.3], "w": list("ABBDD")}).set_index("x")

@pytest.fixture
def sampletbl2(memdb, sampledf2):
    memdb["test2"] = sampledf2
    return memdb["test2"]