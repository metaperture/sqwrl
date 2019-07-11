![sqwrl](https://raw.githubusercontent.com/enkratic/sqwrl/master/sqwrl.png)

# sqwrl
### Sqlachemy Query WRapper Library

### Quickstart

>>> import pandas as pd
>>> from sqwrl import DB
>>> db = DB('sqlite:///:memory:')
>>> df = pd.DataFrame({"x": [1,2,3,4,5], "y": list("abcdf"), "z": [1.0, 1.5, 1.5, 1.2, 1.3]}).set_index("y")
>>> db["test"] = df
>>> tbl = db["test"]
>>> tbl
