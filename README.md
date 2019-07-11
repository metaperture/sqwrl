<img src="https://raw.githubusercontent.com/enkratic/sqwrl/master/sqwrl.png" width="200" height="200">

# sqwrl
### Sqlachemy Query WRapper Library

### Quickstart

```python
import pandas as pd
from sqwrl import DB
db = DB('sqlite:///:memory:')
df = pd.DataFrame({"x": [1,2,3,4,5], "y": list("abcdf"), "z": [1.0, 1.5, 1.5, 1.2, 1.3]}).set_index("y")
ans_df = pd.read_csv("anscombe.csv")
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

See [usage](usage.ipynb) for more usage examples.
