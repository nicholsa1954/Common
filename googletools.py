# -*- coding: utf-8 -*-
"""
packages added for this project:
    gspread-pandas
    gspread-dataframe (with pip)  May have broken the debugger???
    pygsheets

also consider if necessary:
    gspread-formatting (https://gspread-formatting.readthedocs.io/en/latest/)
"""
import datetime
import pathlib
from datetime import datetime

import gspread as gs
import pytz
import requests
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

key_path = '../../Keys/'
key_file = "createapikey-332513-213a2ef92b3e.json"

def WriteToGoogleSheets(df, sheet_id, tab_name, mode, path=key_path):
    file = pathlib.Path(key_file)
    keyfile = pathlib.Path(key_path, file).resolve()

    if keyfile.exists():
        gc = gs.service_account(filename=keyfile)
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}'
        try:
            spreadsheet = gc.open_by_url(url)
        except gs.exceptions.WorksheetNotFound:
            print('WriteToGoogleSheets cant find that spreadsheet!')
            
        if mode == 'w':
            try:
                worksheet = spreadsheet.worksheet(tab_name)
                worksheet.clear()
            except gs.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows = len(df)+1, cols = len(df.columns))
            ### resize = True sets the worksheet size to the dataframe size
            set_with_dataframe(worksheet, df, include_index = False, 
                               include_column_header=True, resize=True)
            return True
            
        elif mode == 'a':
            try:
                worksheet = spreadsheet.worksheet(tab_name)  
                count = worksheet.row_count
                worksheet.add_rows(len(df))
                ## for some reason, need to re-initialize the worksheet
                ## https://stackoverflow.com/questions/67343865/gspread-exceptions-apierror-exceeds-grid-limits-adding-new-rows-and-dataframe
                worksheet = spreadsheet.worksheet(tab_name)
                set_with_dataframe(worksheet, df, include_index=False,
                                   include_column_header=False,
                                   row = count + 1,
                                   resize=False)                
            except gs.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows = len(df)+1, cols = len(df.columns))
                set_with_dataframe(worksheet, df, include_index = False, 
                                   include_column_header=True, resize=True)
            return True
    else: print('WriteToGoogleSheets failed finding keyfile', keyfile)


def ReadDictFromGoogleSheets(sheet_id, tab_names,  path=key_path):
    data_dict = {}
    file = pathlib.Path(key_file)
    keyfile = pathlib.Path(key_path, file).resolve()

    if keyfile.exists():
        gc = gs.service_account(filename=keyfile)
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}'
        try:
            spreadsheet = gc.open_by_url(url)
        except gs.exceptions.WorksheetNotFound:
            print('ReadFromGoogleSheets cant find that spreadsheet!')

        for tab_name in tab_names:
            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gs.exceptions.WorksheetNotFound:
                print('ReadFromGoogleSheets cant get worksheet',
                      tab_name, 'from spreadsheet!')
    
            print('Getting dataframe for', tab_name, '...')
            data_dict[tab_name] = get_as_dataframe(worksheet, parse_dates=True)
        return data_dict
    else: print('ReadDictFromGoogleSheets failed finding keyfile', keyfile)



def ReadFromGoogleSheets(sheet_id, tab_names, evaluate_formulas = True, path=key_path):
    """
        
    Reads data from Google Sheets and returns a list of DataFrames.

    Args:
        sheet_id (str): The ID of the Google Sheets document.
        tab_names (list): A list of tab names to read data from.
        path (str, optional): The path to the keyfile. Defaults to default_path.

    Returns:
        list: A list of DataFrames, each corresponding to a tab in the Google Sheets document.

    Raises:
        None

    Notes:
        - This function requires the gspread library.
        - The keyfile is used to authenticate with the Google Sheets API.
        - If the keyfile is not found, an error message is printed and the function returns None.
        - If a tab is not found in the Google Sheets document, an error message is printed.

    Args:
        sheet_id (_type_): _description_
        tab_names (_type_): _description_
        path (_type_, optional): _description_. Defaults to default_path.

    Returns:
        _type_: _description_
    """
    
    data = []
    file = pathlib.Path(key_file)
    keyfile = pathlib.Path(key_path, file).resolve()

    if keyfile.exists():
        gc = gs.service_account(filename=keyfile)
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}'
        try:
            spreadsheet = gc.open_by_url(url)
        except gs.exceptions.WorksheetNotFound:
            print('ReadFromGoogleSheets cant find that spreadsheet!')

        for tab_name in tab_names:
            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gs.exceptions.WorksheetNotFound:
                print('ReadFromGoogleSheets cant get worksheet',
                      tab_name, 'from spreadsheet!')
    
            print('Getting dataframe for', tab_name, '...')
            data.append(get_as_dataframe(worksheet, evaluate_formulas = evaluate_formulas, parse_dates=True))
        return data

    else: print('ReadFromGoogleSheets failed finding keyfile', keyfile)
    
    
def GetWkbkUpdateTime(sheet_id, path=key_path):
    file = pathlib.Path(key_file)
    keyfile = pathlib.Path(key_path, file).resolve()

    if keyfile.exists():
        gc = gs.service_account(filename=keyfile)
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}'
        try:
            spreadsheet = gc.open_by_url(url) 
        except gs.exceptions.WorksheetNotFound:
            print('GetWkbkUpdateTime cant find that spreadsheet!')
    
 
        scope = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(keyfile, scope)
        # gc = gs.authorize(credentials)
        # wb = gc.open_by_url(url)
        format_string = '%Y-%m-%dT%H:%M:%S.%fZ'
    
        revisions_uri = f'https://www.googleapis.com/drive/v3/files/{spreadsheet.id}/revisions'
        headers = {'Authorization': f'Bearer {credentials.get_access_token().access_token}'}
        response = requests.get(revisions_uri, headers=headers).json()
        date_string = response['revisions'][-1]['modifiedTime']
        local_tz = pytz.timezone("America/Chicago")
        return datetime.strptime(date_string, format_string).astimezone(local_tz)    
