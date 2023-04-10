import pandas as pd

def SetIntersection(adf, bdf, **kwargs):
    if not kwargs: return pd.merge(adf, bdf, how='inner')
    keys = kwargs.keys()
    if 'on' in keys: return pd.merge(adf, bdf, how = 'inner', on=kwargs['on'])
    elif 'left_on' in keys and 'right_on' in keys:
        return pd.merge(adf, bdf, how = 'inner', left_on=kwargs['left_on'], right_on=kwargs['right_on'])
    else: raise ValueError("acceptable keyword args are 'on', or 'left_on' and 'right_on'")

def SetUnion(adf, bdf, **kwargs):
    if not kwargs: return pd.merge(adf, bdf, how='outer')
    keys = kwargs.keys()
    if 'on' in keys: return pd.merge(adf, bdf, how='outer', on=kwargs['on'])
    elif 'left_on' in keys and 'right_on' in keys:
        return pd.merge(adf, bdf, how='outer', left_on=kwargs['left_on'], right_on=kwargs['right_on'])
    else: raise ValueError("acceptable keyword args are 'on', or 'left_on' and 'right_on'")    

def SetDifference(adf, bdf, **kwargs):
    if not kwargs:
        return pd.merge(adf, bdf, how='outer', indicator=True) \
        .query('_merge == "left_only"') \
        .drop(columns = ['_merge']).reset_index(drop=True)
    keys =kwargs.keys()
    if 'on' in keys:
        return pd.merge(adf, bdf, how='outer', on=kwargs['on'], indicator=True) \
        .query('_merge == "left_only"') \
        .drop(columns = ['_merge']).reset_index(drop=True)
    elif 'left_on' in keys and 'right_on' in keys:
        return pd.merge(adf, bdf, how='outer', left_on=kwargs['left_on'], \
        right_on=kwargs['right_on'], indicator=True) \
        .query('_merge == "left_only"') \
        .drop(columns = ['_merge']).reset_index(drop=True)
    else: raise ValueError("acceptable keyword args are 'on', or 'left_on' and 'right_on'")
	
### Everything in the union of adf, bdf that is not in the intersection of adf, bdf
def SetSymmetricDifference(adf, bdf, **kwargs):
    outer = SetUnion(adf, bdf, **kwargs)
    inner = SetIntersection(adf, bdf, **kwargs)
    return pd.concat([outer, inner]).drop_duplicates(keep=False).reset_index(drop=True)
	
def FilterToInclude(adf, bdf, on):
	return adf[adf[on].isin(bdf[on])]
	
def FilterToExclude(adf, bdf, on):
	test = adf[~adf[on].isin(bdf[on])]
	test.reset_index(drop=True, inplace=True)
	return test

def Query(df, expr, **kwargs):
    orig_columns = df.columns
    df.columns = [column.replace(" ", "_") for column in df.columns]
    df.query(expr, inplace = True)
    df.columns = orig_columns
    df.reset_index(drop = True, inplace = True)
    return df
