<img src="https://raw.githubusercontent.com/enkratic/sqwrl/master/docs/sqwrl.png" width="200" height="200">

# sqwrl
### Sqlachemy Query WRapper Library

### Quickstart

```python
import pandas as pd
from sqwrl import DB
db = DB('sqlite:///:memory:')
df = pd.DataFrame({"x": [1,2,3,4,5], "y": list("abcdf"), "z": [1.0, 1.5, 1.5, 1.2, 1.3]}).set_index("y")
ans_df = pd.read_csv("tests/anscombe.csv")
db["anscombe"] = ans_df
ans_tbl = db["anscombe"]
ans_tbl
```

Now you can (mostly) use the sqwrl table object as if it were a pandas dataframe!

```python
ans_tbl[ans_tbl["dataset"].isin(["I", "II"])][["x", "y"]]
```

Use the `.df` attribute on sqwrl table objects to read their output into pandas DataFrames for any unsupported features.

```python
>>> (ans_tbl.df == ans_df).all().all()
True
```

See [usage](https://nbviewer.jupyter.org/github/enkratic/sqwrl/blob/master/usage.ipynb) for more usage examples.

Basic Features:
 - [x] Smart Pandas like wheres using getitem
 - [x] `.loc` operations
 - [x] Indexing (including reset_index, drops, and appending)
 - [x] Sorting
 - [x] Most arithmetic operations lazily pushed
 - [x] Metadata like length and dtypes

Advanced Features:
 - Groupby
   - [x] Groupby group iteration
   - [x] Groupby aggregation
   - [ ] Groupby aggregation over multiple columns
   - [ ] Groupby group sizes
   - [ ] Groupby transform and apply
 - Joins
   - [ ] Pandas-style joins (have the basic framework in place for this)
 - Mutation
   - [ ] Adding, deleting, and editing columns
   - [ ] Appending existing tables
   - [ ] Deleting or editing based on conditions
