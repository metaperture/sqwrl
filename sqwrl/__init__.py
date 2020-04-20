"""
TODO - basic:
 - tbl.index.name setting
 - tbl adding data - setting columns, appending, etc.
TODO - groupby:
 - groupby options - groupby indexing (esp for expr groupbys)
 - groupby push out VirtualTables
 - groupby aggregate multiple agg types, dict agg
 - groupby transform / apply?
TODO - joins:
 - https://pandas.pydata.org/pandas-docs/stable/merging.html
 - test all hows
 - pd.concat (row-wise: UNION, UNION ALL)
 - pd.merge (https://pandas.pydata.org/pandas-docs/stable/merging.html#database-style-dataframe-joining-merging)
 - todo: move df.join to pd.merge (more general)

"""

import copy
import operator
from functools import wraps, partialmethod, reduce
from collections.abc import Iterable
from warnings import warn
import numbers

import pandas as pd
import numpy as np
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.dialects import mssql, postgresql
import sympy
from toolz import assoc, valfilter
#from odo.backends.sql import types as sa_types
#from odo.backends.sql import discover_typeengine
import datashape

__version__ = "0.1.0"

# -------------------------------------
# COPYING FROM ODO TO REMOVE DEPENDENCY
# from odo https://github.com/blaze/odo/blob/master/odo/backends/sql.py

sa_types = {
    'int64': sa.BigInteger,
    'int32': sa.Integer,
    'int': sa.Integer,
    'int16': sa.SmallInteger,
    'float32': sa.REAL,
    'float64': sa.FLOAT,
    'float': sa.FLOAT,
    'real': sa.FLOAT,
    'string': sa.Text,
    'date': sa.Date,
    'time': sa.Time,
    'datetime': sa.DateTime,
    'bool': sa.Boolean,
    "timedelta[unit='D']": sa.Interval(second_precision=0, day_precision=9),
    "timedelta[unit='h']": sa.Interval(second_precision=0, day_precision=0),
    "timedelta[unit='m']": sa.Interval(second_precision=0, day_precision=0),
    "timedelta[unit='s']": sa.Interval(second_precision=0, day_precision=0),
    "timedelta[unit='ms']": sa.Interval(second_precision=3, day_precision=0),
    "timedelta[unit='us']": sa.Interval(second_precision=6, day_precision=0),
    "timedelta[unit='ns']": sa.Interval(second_precision=9, day_precision=0),
    # ??: sa.types.LargeBinary,
}

sa_revtypes = dict(map(reversed, sa_types.items()))

# Subclass mssql.TIMESTAMP subclass for use when differentiating between
# mssql.TIMESTAMP and sa.TIMESTAMP.
# At the time of this writing, (mssql.TIMESTAMP == sa.TIMESTAMP) is True,
# which causes a collision when defining the sa_revtypes mappings.
#
# See:
# https://bitbucket.org/zzzeek/sqlalchemy/issues/4092/type-problem-with-mssqltimestamp
class MSSQLTimestamp(mssql.TIMESTAMP):
    pass

# Assign the custom subclass as the type to use instead of `mssql.TIMESTAMP`.
mssql.base.ischema_names['TIMESTAMP'] = MSSQLTimestamp

sa_revtypes.update({
    sa.DATETIME: datashape.datetime_,
    sa.TIMESTAMP: datashape.datetime_,
    sa.FLOAT: datashape.float64,
    sa.DATE: datashape.date_,
    sa.BIGINT: datashape.int64,
    sa.INTEGER: datashape.int_,
    sa.BIGINT: datashape.int64,
    sa.types.NullType: datashape.string,
    sa.REAL: datashape.float32,
    sa.Float: datashape.float64,
    mssql.BIT: datashape.bool_,
    mssql.DATETIMEOFFSET: datashape.string,
    mssql.MONEY: datashape.float64,
    mssql.SMALLMONEY: datashape.float32,
    mssql.UNIQUEIDENTIFIER: datashape.string,
    # The SQL Server TIMESTAMP value doesn't correspond to the ISO Standard
    # It is instead just a binary(8) value with no relation to dates or times
    MSSQLTimestamp: datashape.bytes_,
})

precision_types = {
    sa.Float,
    postgresql.base.DOUBLE_PRECISION
}

def precision_to_dtype(precision):
    """
    Maps a float or double precision attribute to the desired dtype.
    The mappings are as follows:
    [1, 24] -> float32
    [25, 53] -> float64
    Values outside of those ranges raise a ``ValueError``.
    Parameter
    ---------
    precision : int
         A double or float precision. e.g. the value returned by
    `postgresql.base.DOUBLE_PRECISION(precision=53).precision`
    Returns
    -------
    dtype : datashape.dtype (float32|float64)
         The dtype to use for columns of the specified precision.
    """
    if isinstance(precision, numbers.Integral):
        if 1 <= precision <= 24:
            return float32
        elif 25 <= precision <= 53:
            return float64
    raise ValueError("{} is not a supported precision".format(precision))

# interval types are special cased in discover_typeengine so remove them from
# sa_revtypes
sa_revtypes = valfilter(lambda x: not isinstance(x, sa.Interval), sa_revtypes)

def discover_typeengine(typ):
    if isinstance(typ, sa.Interval):
        if typ.second_precision is None and typ.day_precision is None:
            return datashape.TimeDelta(unit='us')
        elif typ.second_precision == 0 and typ.day_precision == 0:
            return datashape.TimeDelta(unit='s')

        if typ.second_precision in units_of_power and not typ.day_precision:
            units = units_of_power[typ.second_precision]
        elif typ.day_precision > 0:
            units = 'D'
        else:
            raise ValueError('Cannot infer INTERVAL type with parameters'
                             'second_precision=%d, day_precision=%d' %
                             (typ.second_precision, typ.day_precision))
        return datashape.TimeDelta(unit=units)
    if type(typ) in precision_types and typ.precision is not None:
        return precision_to_dtype(typ.precision)
    if typ in sa_revtypes:
        return datashape.dshape(sa_revtypes[typ])[0]
    if type(typ) in sa_revtypes:
        return sa_revtypes[type(typ)]
    if isinstance(typ, sa.Numeric):
        return datashape.Decimal(precision=typ.precision, scale=typ.scale)
    if isinstance(typ, (sa.String, sa.Unicode)):
        return datashape.String(typ.length, 'U8')
    else:
        for k, v in sa_revtypes.items():
            if isinstance(k, type) and (isinstance(typ, k) or
                                        hasattr(typ, 'impl') and
                                        isinstance(typ.impl, k)):
                return v
            if k == typ:
                return v
    raise NotImplementedError("No SQL-datashape match for type %s" % typ)

# -------------------------------------
# END COPYING FROM ODO
# -------------------------------------

def is_striter(val):
    return isinstance(val, Iterable) and all(isinstance(el, str) for el in val)

def is_iter_notstr(val):
    return isinstance(val, Iterable) and not isinstance(val, str)

def and_(*args):
    return reduce(operator.and_, args)

def _dtype(type_name):
    if type_name == "string":
        type_name = "object"
    return np.dtype(type_name)

class DB:
    def __init__(self, engine, verbose=False, check="auto",
                 autoindex=True):
        if isinstance(engine, str):
            engine = sa.create_engine(engine, echo=verbose)
        else:
            engine.echo = verbose
        self.engine = engine
        if check == "auto":
            try:
                from IPython import get_ipython
                check = get_ipython() is not None
            except ImportError:
                check = False
        self.check = check
        self.autoindex = autoindex

    @property
    def metadata(self):
        return sa.MetaData().reflect(bind=self.engine)

    @property
    def tables(self):
        return self.engine.table_names()

    def __iter__(self):
        return iter(self.tables)
    def __contains__(self, k):
        return k in self.tables
    def __len__(self):
        return len(self.tables)

    def __getitem__(self, k):
        assert not self.check or k in self
        return Table(self.engine, k, check=self.check,
                     index=self.autoindex)
    
    def __setitem__(self, k, v):
        if k not in self:
            metadata, _ = Table.from_df(v, k)
            metadata.create_all(self.engine)
            self[k].append(v)
        else:
            raise NotImplementedError()

_colobjtypes = {
    str: sa.String
}

def to_sqlalchemy_type(s):
    if s.dtype.name in sa_types:
        return sa_types[s.dtype.name]
    el = s.iloc[0]
    if type(el).__name__ in sa_types:
        return sa_types[s.dtype.name]
    for k, v in _colobjtypes.items():
        if isinstance(el, k):
            return v
    raise TypeError("unknown type: %s / %s" % (s.dtype.name, type(el)))

_numeric_types = [typ for typ in sa_types if any(
    typ.startswith(numtyp) for numtyp in ['bool', 'float', 'int', 'timedelta'])]


class VirtualTable:
    def __init__(self, engine, salc, check=True,
                 whereclause=None, from_i=None, to_i=None, 
                 sort_by=[], # (by, asc) tuples
                 index=True, columns=None):
        self.engine = engine
        self.sa = salc
        self._whereclause = whereclause
        self._from_i = from_i
        self._to_i = to_i
        self._sort_by = sort_by

        if isinstance(index, (str, Expression)):
            index = [index]
        if index == True: # auto-detect
            self._ix = [c.name for c in self.sa_columns if c.primary_key]
            self._ixdata = [c for c in self.sa_columns if c.primary_key]
        elif is_striter(index):
            self._ix = list(index)
            self._ixdata = [self.sa_colmap[col] for col in self._ix]
        elif index == False or index is None:
            self._ix = []
            self._ixdata = []
        elif all(isinstance(ix, Expression) for ix in index):
            self._ix = [c.name for c in index]
            self._ixdata = list(index)

        if columns is None:
            self._columns = [c.name for c in self.sa_columns if not c.name in self._ix]
            self._coldata = [c for c in self.sa_columns if not c.name in self._ix]
        elif is_striter(columns):
            self._columns = list(columns)
            self._coldata = [self.sa_colmap[col] for col in self._columns]
        elif all(isinstance(col, Expression) for col in columns):
            self._columns = [c.name for c in columns]
            self._coldata = list(columns)

    def copy(self, **new_attrs):
        new = copy.copy(self)
        for k, v in new_attrs.items():
            setattr(new, k, v)
        return new

    ## column stuffs
    @property
    def sa_columns(self):
        cols = self.sa.columns
        self.__dict__['sa_columns'] = cols
        return cols
    @property
    def sa_colmap(self):
        colmap = {c.name: c for c in self.sa_columns}
        self.__dict__['sa_colmap'] = colmap
        return colmap
    @property
    def columns(self):
        return self._columns
    @columns.setter
    def columns(self, column_names):
        assert len(column_names) == len(self._coldata)
        self._columns = column_names
    def _colmatches(self, col, singleton=False, required=False):
        matches = [datum for name, datum in zip(self._columns, self._coldata)
                   if col == name]
        if required and not matches:
            raise KeyError("key %r not found among %r" % (col, self._columns))
        if singleton:
            if len(matches) > 1:
                raise KeyError("ambiguous key %r among %r" % (col, self._columns))
            matches = matches[0] if matches else None
        return matches
    def rename(self, columns=None):
        if columns is not None:
            if isinstance(columns, Mapping):
                new_cols = [columns.get(col, col) for col in self._columns]
            elif isinstance(columns, Callable):
                new_cols = [columns(col) for col in self._columns]
            else:
                raise TypeError("unknown mapper type: %s" % (type(columns)))
            return self.copy(_columns=new_cols)
        return self
    @property
    def coltypes(self):
        cols = [c for c in self.sa_columns if not c.name in self._ix]
        return pd.Series([str(discover_typeengine(c.type)) for c in cols],
                         index=[c.name for c in cols])
    @property
    def dtypes(self):
        return self.coltypes.map(_dtype)

    def iteritems(self):
        yield from zip(self._columns, self._coldata)
    items = iteritems
    def keys(self):
        yield from self._columns
    __iter__ = keys
    def __getitem__(self, k):
        if isinstance(k, str):
            colmatches = self._colmatches(k, required=True)
            if len(colmatches) == 1:
                return Expression(self, colmatches[0], k)
            else:
                return self.copy(_columns=[k]*len(colmatches), _coldata=colmatches)
        elif is_striter(k):
            new_columns = []
            new_coldata = []
            for el in k:
                colmatches = self._colmatches(el, required=True)
                new_columns += [el] * len(colmatches)
                new_coldata += colmatches
            return self.copy(_columns=new_columns, _coldata=new_coldata)
        elif isinstance(k, slice):
            return self.islice(k)
        elif isinstance(k, Expression):
            return self.where(k)
        return self._loc(k)

    ## indexing
    @property
    def index(self):
        if len(self._ix) == 0:
            return None
        if len(self._ix) == 1:
            return Expression(self, self._ixdata[0], self._ix[0])
        else:
            # multindex...return dataframe??
            return self.copy(_columns=list(_ix), _coldata=list(_ixdata))

    def reset_index(self, drop=False):
        if drop:
            return self.copy(_ix=[], _ixdata=[])
        return self.copy(_ix=[], _ixdata=[], _columns=self._columns + self._ix,
                         _coldata=self._coldata + self._ixdata)

    def set_index(self, keys, drop=True, append=False):
        if isinstance(keys, (str, Expression)):
            keys = [keys]
        new_ix = list(self._ix) if append else []
        new_ixdata = list(self._ixdata) if append else []
        new_columns = list(self._columns)
        new_coldata = list(self._coldata)
        for k in keys:
            if isinstance(k, str):
                new_ixdata.append(self._colmatches(k, singleton=True, required=True))
                new_ix.append(k)
                if drop:
                    ix = new_columns.index(k)
                    new_columns.pop(ix)
                    new_coldata.pop(ix)
            elif isinstance(k, Expression):
                new_ixdata.append(k)
                new_ix.append(k.name)
        return self.copy(_ix=new_ix, _ixdata=new_ixdata,
                         _columns=new_columns, _coldata=new_coldata)

    ## location
    def _lookup(self, k):
        result = self.where(self.index == k).df
        if len(result) == 1: # and not isinstance(k, sa.sql.elements.ClauseElement):
            return result.iloc[0]
        elif len(result) == 0:
            raise KeyError("%r not found in %s" % (k, self.index))
        return result
    def _loc(self, k):
        # actually returns a dataframe/series for lookups
        # .loc[normal loc, columns??]
        if isinstance(k, tuple) and len(k) == 2:
            condition, cols = k
            if isinstance(cols, str) or is_striter(cols):
                return self._loc(condition)[cols]
        if isinstance(k, slice):
            # slice (greater than: less than)
            if k.step is not None:
                return self._loc(slice(k.start, k.stop))[::k.step]
            if k.start is None and k.stop is not None:
                return self.where(self.index <= k.stop)
            if k.start is not None and k.stop is None:
                return self.where(self.index >= k.start)
            if k.start is not None and k.stop is not None:
                return self.where(self.index >= k.start & self.index <= k.stop)
            return self
        if isinstance(k, Expression):
            # boolean array?
            return self.where(k)
        elif is_iter_notstr(k):
            # list of elements
            results = [self._lookup(el) for el in k]
            result = pd.concat([pd.DataFrame([r]) if isinstance(r, pd.Series) else r
                               for r in results])
            result.index.name = self.index.name # ???
            dtypes = dict(zip(self.columns, self.dtypes))
            for col in result.columns:
                result[col] = result[col].astype(dtypes[col])
            return result
            #if all(isinstance(result, pd.Series) for result in results):
            #    return pd.DataFrame([self._lookup(el) for el in k])
            #return pd.concat([self._lookup(el) for el in k]) # if some dfs in mix...
        else:
            # single element?
            return self._lookup(k)
    def islice(self, from_i=None, to_i=None, step=None):
        # !? compound with where?
        if isinstance(from_i, slice) and to_i is None and step is None:
            return self.islice(from_i.start, from_i.stop, from_i.step)
        if step is not None:
            assert step == -1 and self._sort_by
            sort_by = [(by, not asc) for by, asc in self._sort_by]
        else:
            sort_by = self._sort_by
        # negative indexes:
        if (from_i is not None and from_i < 0) or (to_i is not None and to_i < 0):
            l = len(self)
            if from_i is not None and from_i < 0:
                from_i += l
            if to_i is not None and to_i < 0:
                to_i += l
        base_from = 0 if self._from_i is None else self._from_i
        base_to = float('inf') if self._to_i is None else self._to_i
        new_from = base_from + (from_i or 0)
        new_to = base_to if to_i is None else min(base_to, base_from + to_i)
        if new_to == float('inf'):
            new_to = None
        return self.copy(_from_i=new_from or None, _to_i=new_to, _sort_by=sort_by)
    @property
    def iloc(self):
        return Indexer(self.islice)
    @property
    def loc(self):
        return Indexer(self._loc)
    def where(self, where):
        if self._from_i or self._to_i:
            warn("wheres on slices not accurately implemented, use at your own risk")
        if self._whereclause is not None:
            where = self._whereclause & where
        return self.copy(_whereclause=where)
    def head(self, n=5):
        return self.islice(0, n)
    def tail(self, n=5):
        return self.islice(-n)

    ## sorting
    def sort_values(self, by, ascending=True):
        if self._from_i or self._to_i:
            warn("sorts on slices not accurately implemented, use at your own risk")
        if isinstance(by, (str, Expression)):
            by = [by]
            ascending = [ascending]
        elif ascending in {True, False}:
            ascending = [ascending] * len(by)
        sort_by = list(self._sort_by)
        for k, asc in zip(reversed(by), reversed(ascending)):
            if isinstance(k, str):
                colmatch = self._colmatches(k, singleton=True, required=True)
                sort_by.insert(0, (Expression(self, colmatch, k), asc))
            elif isinstance(k, Expression):
                sort_by.insert(0, (k, asc))
            else:
                raise TypeError("unknown type for sort: %s" % type(k))
        return self.copy(_sort_by=sort_by)

    def sort_index(self, ascending=True):
        if self._from_i or self._to_i:
            warn("sorts on slices not accurately implemented, use at your own risk")
        return self.sort_values([Expression(self, datum, ix) for ix, datum in
                                 zip(self._ix, self._ixdata)], ascending=ascending)

    def _query_sorted_by(self, q, by, ascending=True):
        if isinstance(by, (str, Expression)):
            by = [by]
            ascending = [ascending]
        elif ascending in {True, False}:
            ascending = [ascending] * len(by)
        order_by = []
        for k, asc in zip(by, ascending):
            if isinstance(k, str):
                k = self._colmatches(k, singleton=True, required=True)
            elif isinstance(k, Expression):
                k = k.sa
            else:
                raise TypeError("unknown by type: %s" % type(k))
            order_by.append(k if asc else k.desc())
        return q.order_by(*order_by)

    ## query interactions
    def connect(self):
        return self.engine.connect()
    def _select_query(self, what, where=None, from_i=None, to_i=None, groupby=None,
                      sort_by=None, sort_ascending=True):
        if sort_by is not None:
            return self.sort_values(by=sort_by, ascending=sort_ascending)._select_query(
                what, where=where, from_i=from_i, to_i=to_i, groupby=groupby)
        if where is not None:
            return self.where(where)._select_query(what, from_i=from_i, to_i=to_i, groupby=groupby)
        if from_i is not None or to_i is not None:
            return self.islice(from_i, to_i)._select_query(what, groupby=groupby)
        q = sa.select(what).select_from(self.sa)
        # WHERE
        if self._whereclause is not None:
            q = q.where(self._whereclause.sa)
        # LIMIT
        if self._to_i is not None:
            q = q.limit(self._to_i - (self._from_i or 0))
        # OFFSET
        if self._from_i is not None and self._from_i > 0:
            q = q.offset(self._from_i)
        # SORT
        if self._sort_by is not None:
            q = q.order_by(*[by.sa if asc else by.sa.desc() for by, asc in self._sort_by])
        if groupby is not None:
            q = q.group_by(*groupby)
        return q

    def select_row(self, what, **kwargs):
        singleton = not isinstance(what, list)
        if singleton:
            what = [what]
        with self.connect() as conn:
            q = self._select_query(what, **kwargs)
            resp = conn.execute(q).fetchone()
        return resp[0] if singleton else resp

    def iterselect(self, what, **kwargs):
        what_dedup = [el for i, el in enumerate(what) if el not in what[:i]]
        ixs = [what_dedup.index(el) for el in what]
        with self.connect() as conn:
            q = self._select_query(what_dedup, **kwargs)
            #yield from conn.execute(q)
            for row in conn.execute(q):
                yield tuple(row[i] for i in ixs)

    def itertuples(self, index=True, name="Pandas"):
        names = self._ix + self._columns if index else self._columns
        data = self._ixdata + self._coldata if index else self._coldata
        typ = namedtuple(name, names)
        for row in self.iterselect(data):
            yield typ(*row)
    def iterrows(self):
        n_ix = len(self.ix)
        for row in self.iterselect(self._ixdata + self._coldata):
            # !?! multiindex?
            yield row[:n_ix], pd.Series(row[n_ix:], index=self._columns)
    def to_dataframe(self):
        names = self._ix + self._columns
        data = self._ixdata + self._coldata
        df = pd.DataFrame.from_records(list(self.iterselect(data)), columns=list(range(len(names))))
        if len(self._ix) == 1:
            df.set_index(0, inplace=True)
            df.index.name = self._ix[0]
        elif self._ix:
            df.set_index(list(range(len(self._ix))), inplace=True)
            df.index.names = self._ix
        df.columns = self._columns
        if self._from_i is not None and not self._ix:
            df.index += self._from_i
        return df
    @property
    def data(self):
        return self.to_dataframe()
    @property
    def df(self):
        return self.to_dataframe()
    def __len__(self):
        return self.select_row(sa.func.count()) # count(self.sa) ...
    ## other
    def insert(self, rows):
        ins = self.sa.insert()
        with self.connect() as conn:
            conn.execute(ins, rows)
    def append(self, df):
        if df.index.name is None:
            rows = [row.to_dict() for _, row in df.iterrows()]
        else:
            rows = [assoc(row.to_dict(), df.index.name, ix) for ix, row in df.iterrows()]
        self.insert(rows)

    def _agg_pairwise(self, how):
        how = {}.get(how, how)
        cols = self.columns
        fn = getattr(func, how)
        resp = self.select_row([fn(self[col1].sa, self[col2].sa)
                                for col1 in cols for col2 in cols])
        result = pd.DataFrame.from_records([resp[i * len(cols):(i + 1) * len(cols)]
                                            for i in range(len(cols))],
                                           index=cols, columns=cols)
        return result

    def aggregate(self, how, axis=None, skipna=None):
        how = {"mean": "avg", "std": "stddev", "var": "variance"}.get(how, how)
        #assert how in {"min", "max", "avg", "sum"}
        fn = getattr(func, how)
        if axis in {None, 0}:
            cols = self.columns
            vals = self.select_row([fn(self[col].sa) for col in cols])
            return pd.Series(vals, index=cols)
        elif axis == 1:
            agg_sa = fn(*[self[col].sa for col in self.columns])
            return Expression(self, agg_sa, how)
        else:
            raise ValueError("axis not in {None, 0, 1}: %s" % axis)

    def nunique(self, dropna=True):
        cols = self.columns
        vals = self.select_row([func.count(self[col].sa.distinct()) for col in cols])
        return pd.Series(vals, index=cols)
    def groupby(self, by=None, axis=0, level=None, as_index=True,
                sort=True, group_keys=True, squeeze=False, **kwargs):
        return GroupBy(self, by, sort=sort, as_index=as_index)
    def _repr_html_(self):
        df = self.head().df
        if len(self) > len(df):
            df = df.append(pd.Series("...", index=df.columns, name="..."))
        return df._repr_html_()
    def alias(self, name=None):
        new_sa = self.sa.alias(name=name)
        new_cols = new_sa.columns
        new_ixdata = [getattr(new_cols, c.name) for c in self._ixdata]
        new_coldata = [getattr(new_cols, c.name) for c in self._coldata]
        # !?!? derived columns?
        return self.copy(sa=new_sa, _ixdata=new_ixdata, _coldata=new_coldata)
    def join(self, other, on=None, how="left", lsuffix='', rsuffix='', sort=False):
        assert how in {'left', 'right', 'outer', 'inner'}
        if how == "right":
            return other.join(self, on=on, how="left", lsuffix=rsuffix, rsuffix=lsuffix, sort=sort)
        alias_self = self.alias()
        alias_other = other.alias()
        if on is None:
            assert set(alias_self._ix) == set(alias_other._ix), "mismatched indexes"
            on_clause = and_(*[ixdata == alias_other._ixdata[alias_other._ix.index(ix)]
                               for ix, ixdata in zip(alias_self._ix, alias_self._ixdata)])
        else:
            if isinstance(on, str):
                on = [on]
            on_clause = and_(*[alias_self[col].sa == alias_other[col].sa for col in on])
            
        col_overlap = set(alias_self.columns) & set(alias_other.columns)
        if col_overlap:
            assert lsuffix or rsuffix, "columns overlap but no suffix specified"
            self_columns = [str(col) + lsuffix if col in col_overlap else col
                            for col in alias_self.columns]
            other_columns = [str(col) + rsuffix if col in col_overlap else col
                             for col in alias_other.columns]
            new_cols = self_columns + other_columns
        else:
            new_cols = alias_self.columns + alias_other.columns
        # TODO: select the right columns from self and other, not just table selection
        #  - ?? only if columns have been selected???
        new_sa = alias_self.sa.join(alias_other.sa, on_clause, isouter=(how != "inner"), full=(how == "outer"))
        # TODO: test all hows
        # ?? error in primary keys with new table creation?
        new_table = VirtualTable(self.engine, new_sa, index=False)
        for col in new_table._coldata:
            pass
        #new_table.columns = new_cols
        #onlen = len(alias_self._ix) if on is None else len(on)
        #new_table._ix, new_table._ixdata = new_table._ix[:onlen], new_table._ixdata[:onlen]
        if sort:
            new_table = new_table.sort_index()
        return new_table

class Table(VirtualTable):
    @staticmethod
    def from_df(df, name, metadata=None):
        metadata = sa.MetaData() if metadata is None else metadata
        cols = [sa.Column(col, to_sqlalchemy_type(df[col])) for col in df.columns]
        if df.index.name is not None:
            ix = df.index.to_series()
            cols = [sa.Column(ix.name, to_sqlalchemy_type(ix), primary_key=ix.is_unique)] + cols
        return metadata, sa.Table(name, metadata, *cols)

    def __init__(self, engine, table, **kwargs):
        salc = sa.Table(table, sa.MetaData(), autoload=True, autoload_with=engine)
        super().__init__(engine, salc, **kwargs)

class Expression:
    def __init__(self, table, salc, name):
        self.table = table
        self.sa = salc
        self.name = name
    def copy(self, **new_attrs):
        new = copy.copy(self)
        for k, v in new_attrs.items():
            setattr(new, k, v)
        return new
    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, repr(self.sa))
    def __len__(self):
        with self.table.connect() as conn:
            q = self.table._select_query([sa.func.count(self.sa)])
            return conn.execute(q).fetchone()[0]
    def __iter__(self):
        with self.table.connect() as conn:
            q = self.table._select_query([self.sa])
            return iter(val for (val,) in conn.execute(q))
    def iteritems(self):
        with self.table.connect() as conn:
            if self.table._ix:
                ixs = self.table._ixdata
                q = self.table._select_query(ixs + [self.sa])
                if len(ixs) == 1:
                    return iter(conn.execute(q))
                return iter((row[:-1], row[-1]) for row in conn.execute(q))
            else:
                from_i = self.table._from_i or 0
                q = self.table._select_query([self.sa])
                return iter((i, val) for
                            (i, (val,)) in enumerate(conn.execute(q), from_i))
    def __getitem__(self, k):
        if isinstance(k, slice) or isinstance(k, Expression):
            return self.copy(table=self.table[k])
        raise TypeError("unrecognized key type: %s" % type(k))
    def to_series(self):
        tbl = self.table
        vals = []
        ixs = []
        for ix, val in self.iteritems():
            vals.append(val)
            ixs.append(ix)
        if len(tbl._ix) < 2:
            name = tbl._ix[0] if tbl._ix else None
            ix = pd.Index(ixs, name=name)
        else:
            ix = pd.MultiIndex.from_tuples(ixs, names=tbl._ix)
        return pd.Series(vals, index=ix, name=self.name)
    @property
    def data(self):
        return self.to_series()
    @property
    def s(self):
        return self.data
    @property
    def dtype(self):
        return np.dtype(str(discover_typeengine(self.sa.type)))
    @property
    def iloc(self):
        return Indexer(self.islice)
    def _lookup(self, k):
        tbl = self.table
        select = self.copy(table=tbl.where(tbl.index == k))
        result = select.s
        if len(result) == 0:
            raise KeyError("%r not found in %s" % (k, tbl.index))
        return result
    def _loc(self, k):
        # actually returns a series/values for lookups
        if isinstance(k, (slice, Expression)):
            return self.copy(table=self.table._loc(k))
        elif is_iter_notstr(k):
            # list of elements
            return pd.concat([self._lookup(el) for el in k])
        else:
            # single element
            result = self._lookup(k)
            return result.iloc[0] if len(result) == 1 else result
    @property
    def loc(self):
        return Indexer(self._loc)
    def aggregate(self, how, axis=None, skipna=None):
        how = {"mean": "avg", "std": "stddev", "var": "variance"}.get(how, how)
        assert axis in {0, None}
        fn = getattr(func, how)
        return self.table.select_row(fn(self.sa))

    def nunique(self, dropna=True):
        return len(self.unique())
    def isnull(self):
        return (self == None)
    isna = isnull
    def notnull(self):
        return (self != None)
    notna = notnull
    def sort_values(self, ascending=True):
        assert ascending in {True, False}
        return self.copy(table=self.table.sort_values(self, ascending=ascending))
    def nlargest(self, n=5):
        return self.sort_values(ascending=False).head(n)
    def nsmallest(self, n=5):
        return self.sort_values(ascending=True).head(n)
    def groupby(self, by=None, axis=0, level=None, as_index=True,
                sort=True, group_keys=True, squeeze=False, **kwargs):
        return GroupBy(self, by, sort=sort, as_index=as_index)

# operator overloading
for opname in ["lt", "le", "gt", "eq", "ge", "ne",
               "mul", "add", "sub", "truediv", "pow",
               "and_", "or_"]:
    op = getattr(operator, opname)
    def fn(self, other, op=op):
        if hasattr(other, "sa"):
            new_sa = op(self.sa, other.sa)
            new_name = self.name if other.name == self.name else None
        else:
            new_sa = op(self.sa, other)
            new_name = self.name
        return Expression(self.table, new_sa, new_name)
    setattr(Expression, "__%s__" % opname.strip("_"), fn)

# pass-through to underlying table
for method in ["head", "tail", "islice", "sort_index", "where"]:
    tbl_fn = getattr(Table, method)
    @wraps(tbl_fn)
    def fn(self, *args, tbl_fn=tbl_fn, **kwargs):
        return self.copy(table=tbl_fn(self.table, *args, **kwargs))
    setattr(Expression, method, fn)
for sql_func in ["rank"]:
    op = getattr(func, sql_func)
    def fn(self, op=op):
        return Expression(self.table, op(self.sa), self.name)
    setattr(Expression, sql_func, fn)
for sql_method in ["startswith", "endswith", "in_"]:
    method = getattr(sa.sql.operators.ColumnOperators, sql_method)
    @wraps(method)
    def fn(self, *args, _method=method, **kwargs):
        return Expression(self.table, _method(self.sa, *args, **kwargs), self.name)
    setattr(Expression, sql_method, fn)
for sql_method in ["distinct"]:
    method = getattr(sa.sql.operators.ColumnOperators, sql_method)
    @wraps(method)
    def fn(self, *args, _method=method, **kwargs):
        return Expression(self.table.reset_index(), _method(self.sa, *args, **kwargs), self.name)
    setattr(Expression, sql_method, fn)
Expression.isin = Expression.in_
Expression.unique = Expression.distinct

class Indexer:
    def __init__(self, getter, setter=None):
        self.getter = getter
        self.setter = setter
    def __getitem__(self, k):
        return self.getter(k)

class GroupBy:
    def __init__(self, base, by, sort=True, as_index=True):
        assert isinstance(base, (Table, Expression))
        self.base = base
        if isinstance(by, (str, Expression)):
            by = [by]
        self.by = [base[k] if isinstance(k, str) else k for k in by]
        self.sort = sort
        self.as_index = as_index
    def __getitem__(self, k):
        if isinstance(self.base, Table):
            if isinstance(k, str) or is_striter(k):
                return GroupBy(self.base[k], self.by)
        raise TypeError("unrecognized key type %s for groupby base type %s" %
                        (type(k), type(self.base)))
    @property
    def table(self):
        return self.base if isinstance(self.base, Table) else self.base.table

    def get_group(self, group):
        singleton = len(self.by) == 1
        if singleton and (isinstance(group, str) or not isinstance(group, Iterable)):
            group = [group]
        condition = and_(*[by_el == group_el for by_el, group_el in zip(self.by, group)])
        return self.base.where(condition)

    @property
    def groups(self):
        by = [by.sa for by in self.by]
        singleton = len(self.by) == 1
        groups = list(self.table.iterselect(by, groupby=by))
        return {group[0] if singleton else group:
                and_(*[by_el == group_el for by_el, group_el in zip(self.by, group)])
                for group in groups}

    def __len__(self):
        by = [by.sa for by in self.by]
        q = self.table._select_query(by, groupby=by).count()
        with self.table.connect() as conn:
            return conn.execute(q).fetchone()[0]

    def __iter__(self):
        by = [by.sa for by in self.by]
        singleton = len(self.by) == 1
        sort_by = self.by if self.sort else None
        for group in self.table.iterselect(by, groupby=by, sort_by=sort_by):
            condition = and_(*[by_el == group_el for by_el, group_el in zip(self.by, group)])
            yield group[0] if singleton else group, self.base.where(condition)
    def apply(self, func, *args, **kwargs):
        return pd.concat([func(data.data, *args, **kwargs) for _, data in self])
    def transform(self, func, *args, **kwargs):
        return pd.concat([func(data.data, *args, **kwargs) for _, data in self])
    def size(self):
        bynames = [by.name for by in self.by]
        by = [by.sa for by in self.by]
        vals = []
        ixs = []
        for row in self.table.iterselect(by + [sa.func.count()], groupby=by): # TODO !!, sort_by=sort_by):
            vals.append(row[-1])
            ixs.append(row[:-1])
        if len(bynames) < 2:
            ix = pd.Index(ixs, name=bynames[0])
        else:
            ix = pd.MultiIndex.from_tuples(ixs, names=bynames)
        return pd.Series(vals, index=ix)

    def aggregate(self, how, as_df=True):
        # TODO: multiple hows, how dicts...
        how = {"mean": "avg", "std": "stddev", "var": "variance"}.get(how, how)
        valid_types = _numeric_types if how in {"avg", "stddev", "variance", "sum"} else sa_types
        fn = getattr(func, how)
        by = [by.sa for by in self.by]
        bynames = [by.name for by in self.by]
        # TODO: return as synthetic table?
        # class VirtualTable - has a base for queries (sa), and a bunch of columns
        if isinstance(self.base, Table):
            colnames = [col for col, dtype in zip(self.base.columns, self.base.coltypes) if dtype in valid_types
                        and not col in bynames]
            salc = [by.sa for by in self.by] + [fn(self.base[col].sa) for col in colnames]
        else:
            colnames = [self.base.name]
            salc = [by.sa for by in self.by] + [fn(self.base.sa)]
        ix = self.by if self.as_index else None
        sort_by = self.by if self.sort else None
        if not as_df:
            new_q = self.table._select_query(salc, groupby=by, sort_by=sort_by)
            new_sa = new_q #.from_self()
            vt = VirtualTable(self.table.engine, new_sa)
            vt._ixdata, vt._coldata = vt._coldata[:len(bynames)], vt._coldata[len(bynames):]
            vt._ix, vt._columns = bynames, colnames
            if not self.as_index:
                vt = vt.reset_index()[bynames + colnames]
            return vt

        df = pd.DataFrame.from_records(list(self.table.iterselect(salc, groupby=by, sort_by=sort_by)),
                                       columns=list(range(len(salc))))
        if self.as_index:
            df.set_index(list(range(len(self.by))), inplace=True)
            df.index.names = bynames
            df.columns = colnames
        else:
            df.columns = bynames + colnames
        if not isinstance(self.base, Table) and self.as_index:
            return df[colnames[0]]
        return df
    agg = aggregate

for agg_fn in ["min", "max", "mean", "sum", "std", "var", "count"]:
    def wrapped(self, axis=None, skipna=None, how=agg_fn):
        return self.aggregate(how, axis=axis, skipna=skipna)
    wrapped.__name__ = agg_fn
    setattr(Table, agg_fn, wrapped)
    setattr(Expression, agg_fn, wrapped)
    setattr(GroupBy, agg_fn, partialmethod(GroupBy.aggregate, how=agg_fn))

for pair_agg_fn in ["corr", "cov"]:
    def wrapped(self, how=pair_agg_fn):
        return self._agg_pairwise(how)
    wrapped.__name__ = pair_agg_fn
    setattr(Table, pair_agg_fn, wrapped)
