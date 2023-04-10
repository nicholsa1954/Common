
import pandas as pd
import pathlib
from pathlib import Path
import phonenumbers
import time
from time import strftime, gmtime
import datetime
from datetime import date, datetime, timedelta, timezone
import pytz
import json
import numpy as np
import pathlib


import sys
sys.path.append('./')
from testVPNConnection import testVPNConnection

epochDate = '1970-01-01 00:00:00'
cutoffDate = '2021-11-01 00:00:00'

beginningOfTime = datetime.fromisoformat(epochDate)
empowerCutoffDate = datetime.fromisoformat(cutoffDate)

"""
def Op1(x): return x*x
def Op2(x): return x*x*x

def Func(row, headers, ops):
    vals = []
    assert len(headers) == len(ops), 'mismatch in number of columns, operations'
    for i in range(len(headers)):
        vals.append( ops[i](row[headers[i]]) )
    return pd.Series(vals)


headers = ['col1','col2']
ops = [Op1, Op2]
data = {headers[0]:[1,2,3], headers[1]:[4,5,6]}
df = pd.DataFrame(data)

df[['col3', 'col4']] = df.apply(lambda row : Func(row, headers, ops), axis = 1)
df

"""

class DatetimeRange:
    def __init__(self, dt1, dt2):
        self._dt1 = dt1
        self._dt2 = dt2

    def __contains__(self, dt):
        return self._dt1 <= dt < self._dt2

    def print(self):
        return(''.join(['[', str(self._dt1), ' - ', str(self._dt2), ')']))

def ConvertNaiveDatesToUtc(df, date_columns, date_only = True):
    for column in date_columns:
        if date_only:
            df.loc[:, column] = df.loc[:, column].apply(lambda x : pd.to_datetime(x).date())
        else:
            df.loc[:, column] = df.loc[:, column].apply(lambda x : pd.to_datetime(x))
    return df

def ConvertUtcDatesToNaive(df):
    date_columns = df.select_dtypes(include=['datetime64[ns, UTC]']).columns
    for date_column in date_columns:
        df.loc[:, date_column] = df.loc[:, date_column].dt.date
    return df

def IsBlank(s):
    if isinstance(s, float) or isinstance(s, int): return True
    try:
        return bool(not s or s.isspace())
    except ValueError:
        print(type(s))


def IsNotBlank(s):
    if isinstance(s, float) or isinstance(s, int): return False
    return bool(s and not s.isspace())


def ConvertTime(theTime):
    try:
        if np.isnan(theTime):
            return datetime.fromisoformat('1970-01-01 00:00:00').date()
        if isinstance(theTime, int) or isinstance(theTime, float):
            return pd.to_datetime(strftime("%Y-%m-%d",gmtime(int(theTime/1000)))).date()
        if IsBlank(theTime):
            return datetime.fromisoformat('1970-01-01 00:00:00').date()
    except TypeError: # handle something like 2021-04-03 21:58:01 +0000
        date, time, _ = theTime.split()
        return datetime.fromisoformat(' '.join([date, time])).date()

def ConvertToDatetime(columns_to_convert, df):
    for col_name in columns_to_convert:
        indx = list(df.columns).index(col_name)
        series = df[col_name].apply(lambda x : ConvertTime(x))
        df.drop(columns = col_name, inplace = True)
        df.insert(indx, col_name, series)
    return df

def ParsePhoneUS(phone_number):
    # default_phone = '(000) 000-0000'
    default_phone = ''
    if isinstance(phone_number, float) or isinstance(phone_number, int): return default_phone
    assert(isinstance(phone_number, str))
    if phone_number == 'None' or phone_number == 'nan' or IsBlank(phone_number): return default_phone
    if(len(phone_number) > 10 and phone_number[0] == '1'):
        phone_number = phone_number[1:]
    if len(phone_number) > 10  and phone_number[-1] == '0':
        phone_number = phone_number[:10]
    try:
        my_number = phonenumbers.parse(phone_number, region = 'US')
        return phonenumbers.format_number(my_number, phonenumbers.PhoneNumberFormat.NATIONAL)
    except phonenumbers.NumberParseException:
        return default_phone

def CleanPhone(df, phone_column = 'phone'):
    column_list = list(df.columns)
    default_phone = ''
    if phone_column in column_list:
        indx = column_list.index(phone_column)
        df[phone_column] = df[phone_column].astype(str)
        df[phone_column] = df[phone_column].fillna(default_phone)
        df['phone_clean'] = df[phone_column].apply(lambda x : ParsePhoneUS(x))
        df.drop(columns = [phone_column], inplace = True)
        df.rename(columns = {'phone_clean':phone_column}, inplace = True)
        df.insert(indx, phone_column, df.pop(phone_column))
    return df
    
"""
usage: df = InitializeDataFrames(path, file, True, {'sheet_name': '<SheetName>'})
"""    
def InitializeDataFrames(path, data_file, remote_file = True, kwargs={}):
    if remote_file and not testVPNConnection():
        print('No VPN connection -- returning empty DataFrame.')
        return pd.DataFrame()
    if not Path(path).exists():
        print("Can't find the path:", path,'-- returning empty DataFrame.')
        print('Do you need to enter network credentials?')
        return pd.DataFrame()
    inFile = Path(path + data_file)
    if not inFile.is_file():
        print("Can't find the file:", inFile, '-- returning empty DataFrame.')
        print('Do you need to enter network credentials?')
        return pd.DataFrame()
    print('Loading data from file...')

    sfx = pathlib.Path(data_file).suffix
    start = time.time()
    if sfx == '.json':
        df = pd.read_json(inFile, typ = 'series', orient = 'records', **kwargs)
    elif sfx == '.csv':
        df = pd.read_csv(inFile,  **kwargs)
    elif sfx == '.xlsx':
        df = pd.read_excel(inFile, **kwargs)
    print('Data loaded, elapsed time:', round((time.time() - start), 2), 'seconds.')
    return df


def InsertDataAtIndex(df, index, label, data):
    df.insert(index, label, data)
    return df

def InsertDataAtLabel(df, new_label, next_to_label, data):
    df[new_label] = data
    col = df.columns.tolist()
    ndx = list(df.columns).index(next_to_label)+1
    col.insert(ndx, col.pop()) #loc is the column's index you want to insert into
    df = df[col]
    return df
