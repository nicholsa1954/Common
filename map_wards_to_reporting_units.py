import numpy as np
import re
import sys
import pandas as pd
sys.path.append('../../Common')

from edatools import InitializeDataFrames, ColumnMove
from setoperations import SetIntersection, SetDifference

common_epsg = 4326  #3070 is the Wisconsin Mercator Projection
common_crs = f'EPSG:{common_epsg}'

wisconsin_epsg = 3070
wisconsin_crs = f'EPSG:{wisconsin_epsg}'

from ward_mappings import ward_mappings
keys = ward_mappings.keys()

def InitializeWECDataFrames(path, file, geocodes, label_row, body_row,   presidential, remote_file, kwargs):
    df = InitializeDataFrames(path, file,  remote_file, kwargs = kwargs)
    label = df.iloc[label_row,0].title()
    columns_to_keep = ['WEC Canvass Reporting System', 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3','Unnamed: 4',] #'Total Votes Cast', 'DEM', 'REP'   
    columns_renamed = ['CNTY_NAME', 'ReportingUnit', 'TotalVotes', 'DEM', 'REP']
    df = df[columns_to_keep]
    df.rename(columns = dict(zip(columns_to_keep, columns_renamed)), inplace = True)
    df = df.iloc[body_row:]
    df.reset_index(drop=True, inplace=True)
    
    if presidential:
        dem_name = 'Kamala_Harris'
        rep_name = 'Donald_Trump'
        
    else:
        dem_name = '_'.join(''.join(df.iloc[0,3]).split())
        rep_name = '_'.join(''.join(df.iloc[0,4]).split())
    
    df = df.iloc[1:]
    df.reset_index(drop=True, inplace=True)
    
    office_totals = df.loc[len(df) - 1]
    df = df.loc[(df['ReportingUnit'] != 'County Totals:') & (df['CNTY_NAME'] != 'Office Totals:') & (df['ReportingUnit'].notna())]
    df['DEM'] = df['DEM'].astype(int)
    df['REP'] = df['REP'].astype(int)
    df['TotalVotes'] = df['TotalVotes'].astype(int)
    df['CNTY_NAME'] = df['CNTY_NAME'].ffill().str.title()
    df['CNTY_NAME'] = df['CNTY_NAME'].apply(lambda x: f"{x.strip()} County")
    df['CNTY_NAME'] = df['CNTY_NAME'].replace('Fond Du Lac County', 'Fond du Lac County')
    df['CNTY_FIPS'] = ''
    df = ColumnMove(df, 'CNTY_FIPS', 1)
    df.reset_index(drop=True, inplace=True)

    for row in geocodes.itertuples():
        df.loc[df['CNTY_NAME'] == row.Area_Name,'CNTY_FIPS'] = row.GEOID

    df['ReportingUnit'] = df['ReportingUnit'].str.title()
    df['ReportingUnit'] = df['ReportingUnit'].str.replace('Of', 'of')
    df['ReportingUnit'] = df['ReportingUnit'].str.replace(' Du ', ' du ')
    df = pd.concat([df, df['ReportingUnit'].apply(lambda s: pd.Series(ProcessReportingUnitString(s),dtype='object'))], axis=1)
    df['Wards'] = df.apply(ConvertWardFormat, args=(ConvertWardStrings,), axis=1)
    df['data'] = df['data'].astype(str)
    df['data'] = df['data'].fillna('None')
    df['MCD_NAME'] = df['ReportingUnit'].map(ConvertRow)
    df['MCD_FIPS'] = '0'
    df['EXPANDEDGEOID'] = '0'

    ### Put a county code on each MCD so we can distinguish similarly named MCDs in different counties
    ### Match by the name of the MCD
    diff = SetDifference(df, geocodes[['Area_Name', 'County_Code']], left_on = 'CNTY_NAME', right_on = 'Area_Name')
    df = SetIntersection(df, geocodes[['Area_Name', 'County_Code']], left_on = 'CNTY_NAME', right_on = 'Area_Name')

    #add the fips codes for the MCDs
    for row in geocodes.itertuples():
        df.loc[(df['MCD_NAME'] == row.MCD_NAME) & (df['County_Code'] == row.County_Code), 'MCD_FIPS'] = row.GEOID
        
    df['EXPANDEDGEOID'] = df.apply(ExpandFips, axis=1)
    
    columns_to_keep2 = [\
    'CNTY_NAME', 'CNTY_FIPS',  'MCD_NAME', 'MCD_FIPS', 
    'TotalVotes', 'DEM', 'REP', 'Wards', 'EXPANDEDGEOID'] 

    df = df[columns_to_keep2]
    if presidential:
        df = df.rename(columns = {'TotalVotes':'PresTotalVotes', 'DEM':'PresDEM', 'REP':'PresREP'})
    else:
        df = df.rename(columns = {'TotalVotes':'DistTotalVotes', 'DEM':'DistDEM', 'REP':'DistREP'})
        
    return label, dem_name, rep_name, office_totals, df     

def PreprocessData(df, str_to_append, target_county_list):
    """
    Preprocess election results data by renaming columns, stripping/titlecasing county names, 
    title-casing reporting units, and removing rows not in target_county_list.  Also, separate
    a df_totals dataframe from the main df, which contains the county totals.
    
    Parameters
    ----------
    df : pandas DataFrame
        Election results data
    target_county_list : list
        List of target counties
        
    Returns
    -------
    df_totals : pandas DataFrame
        County totals
    df : pandas DataFrame
        Preprocessed election results data
    """
    
    total_column_name = ' '.join(['Total', str_to_append])
    df.rename(columns={'Unnamed: 0': 'CNTY_NAME', 'Unnamed: 1': 'ReportingUnit', 
            'Unnamed: 2': total_column_name, 'SCATTERING': 'Other'}, inplace=True)
    df['CNTY_NAME'] = df['CNTY_NAME'].str.strip().ffill()
    df['CNTY_NAME'] = df['CNTY_NAME'].apply(lambda x: x.strip().title())

    df['ReportingUnit'] = df['ReportingUnit'].ffill()
    df['ReportingUnit'] = df['ReportingUnit'].apply(lambda x: x.title())
    df['ReportingUnit'] = df['ReportingUnit'].str.replace("Of","of")
    df = df.loc[df['CNTY_NAME'].isin(target_county_list)].reset_index(drop=True)
    df['CNTY_NAME'] = df['CNTY_NAME'].apply(lambda x: f"{x} County")
    df_totals = df.loc[df['ReportingUnit'] == 'County Totals:']
    df = df.loc[df['ReportingUnit'] != 'County Totals:']
    return df_totals, df

def extract_numbers(text):
    """Extracts numbers from a string with hyphenated ranges.

    Args:
    text: The input string.

    Returns:
    A string composed from a list of numbers.
    """
    numbers = []
    for part in re.findall(r'\d+-\d+|\d+', text):
        if '-' in part:
            start, end = map(int, part.split('-'))
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(int(part))
    return ','.join(map(str,numbers)) if numbers else None

def ProcessReportingUnitString(ward):
    """
        Process a reporting unit string into a dictionary with two keys: 'type' and 'data'.

        'type' is one of the following:
            - commahyphen: ward contains both '-' and ',' e.g. 'foo bar bazz 1-3,5-7,9'
            - hypen: ward contains '-' but not ',' e.g. 'foo bar bazz 1-3'
            - single: ward contains a single digit e.g. 'foo bar bazz 1'
            - amp: ward contains '&' but not '-' or ',' e.g. 'foo bar bazz 1&2'
            - comma: ward contains ',' but not '-' or '&' e.g. 'foo bar bazz 1,2'
            - unmatched: ward does not contain any of the above, and is returned as is

        'data' is a string containing the extracted numbers or the original string if 'type' is 'unmatched'.

        :param ward: A string representing a reporting unit.
        :return: A dictionary with two keys: 'type' and 'data'.
        :raises Exception: If the input string is None or empty.
        """
    if ward in ['County Totals:', 'Office Totals:']:
        pass
    elif ward != np.nan:
        # not None if ward contants both '-' and ',' e.g. 'foo bar bazz 1-3,5-7,9'
        regexpn = r"(,.*-)|(-.*,)"
        x = re.search(regexpn, ward)
        if x is not None:
            if result := extract_numbers(ward): 
                return {"type": "commahyphen", "data": result}
            raise Exception()
        else:
            # not None if ward contains '-' or '&' or ',' or a single digit
            regexpn2 = r"((?:^\D+)(?P<hypen>(\d+)(?:\s*)-(?:\s*)(\d+$)))|((?:^\D+)(?P<single>(\d+$)))|((?:^\D+)(?P<amp>(\d+)(?:\s*)&(?:\s*)(\d+$)))|((?:^\D+)(?P<comma>(\d+)(?:,\d+)*))"
            x = re.search(regexpn2, ward)
            if x is None:
                return {"type": "unmatched", "data": ward}
            elif x.group('single'):
                return {"type": "single", "data": x.group('single')}
            elif x.group('hypen'):
                return {"type": "hypen", "data": x.group('hypen')}
            elif x.group('amp'):
                return {"type": "amp", "data": x.group('amp')}
            elif x.group('comma'):
                return {"type": "comma", "data": x.group('comma')}
            else:
                raise Exception()
    else:
        raise Exception()
    

def ProcessReportingUnitData(df, wards_df, data_column_list, 
        ward_fips_list = None, cleanup_redundant_columns = True,
        keep_geometry = False):  
    """
    Process reporting unit data by distributing values proportionally based on VAP.

    This function processes reporting unit data where the EXPANDEDGEOID represents multiple wards.
    It distributes values from columns in data_column_list proportionally to each 
    ward based on the VAP (Voting Age Population) given in `wards_df`.

    Args:
        df: DataFrame containing reporting unit data.
        wards_df: DataFrame containing ward-level VAP data.
        data_column_list: List of columns to distribute values from.
        ward_fips_list: List of ward FIPS codes to consider. If None, all wards are considered.

    Returns:
        DataFrame with values distributed from reporting units to individual wards based on VAP.
    """
    df_all = pd.DataFrame()
    for row in df.itertuples(index=False):
        if len(row.EXPANDEDGEOID) <= 14: 
            frame = pd.Series(row).to_frame().T
            frame.columns = df.columns
            df_all = pd.concat([df_all, frame], axis=0, ignore_index=True)  

    for row in df.itertuples(index=False):
        if len(row.EXPANDEDGEOID) > 14:
            geoValues = row.EXPANDEDGEOID.split('|')
            if ward_fips_list is not None:
                df_row = wards_df.loc[(wards_df['GEOID'].isin(geoValues)) & 
                                    (wards_df['WARD_FIPS'].isin(ward_fips_list))]
            else:
                df_row = wards_df.loc[wards_df['GEOID'].isin(geoValues)]
            total_vap = df_row['PERSONS18'].sum()
            for r in df_row.itertuples(index=False):
                frame = pd.Series(row).to_frame().T
                frame.columns = df.columns  
                if total_vap > 0:
                    vap_fraction = r.PERSONS18 / total_vap 
                else:
                    vap_fraction = 0
                for col in data_column_list:
                    frame[col] = int(frame[col] * vap_fraction)
                frame['EXPANDEDGEOID'] = r.GEOID
                frame['Wards'] = ' '.join(['Ward', r.GEOID[-1]])
                df_all = pd.concat([df_all, frame], axis=0, ignore_index=True)  

    df_all['GEOID'] = df_all['EXPANDEDGEOID']
    if cleanup_redundant_columns:
        df_all.drop(columns=['EXPANDEDGEOID', 'Wards'], inplace=True)
    df_all = ColumnMove(df_all, 'GEOID', 0)
    df_all.sort_values(by=['CNTY_FIPS', 'MCD_FIPS', 'GEOID'], inplace=True)
    df_all.reset_index(drop=True, inplace=True)
    if keep_geometry:
        return SetIntersection(df_all, wards_df[['GEOID', 'geometry']], on='GEOID')
    return df_all

        
def ConvertWardStrings(row):
    """
    Converts a ward string into a standardized ward format using a predefined mapping.

    Args:
    row: A string representing a ward.

    Returns:
    A string from the ward_mappings dictionary that corresponds to the input ward string.

    Raises:
    Exception: If the input ward string is not found in the ward_mappings dictionary.
    """
    x = re.search(r'(^\D+)', row)
    pos = row.find('Ward')
    startrow = row[:pos]
    subrow = row[pos:]
    if subrow in keys:
        return ward_mappings[subrow]
    else:
        raise Exception(row, subrow, 'not in dictionary')
    
def ConvertWardFormat(row, converter):
    """
    Converts a ward string into a standardized ward format using a predefined mapping.

    Args:
        row: A dictionary with two keys: 'type' and 'data'. The 'type' key
            has a string value that indicates the type of ward format, and the
            'data' key has a string value that represents the ward in that
            format.

    Returns:
        A string in the standardized ward format that corresponds to the input
        ward string.

    Raises:
        Exception: If the input ward string is not found in the ward_mappings
            dictionary.
    """
    try:
        if row['type'] == 'hypen':
            search = re.search(r'(\d+)(?:\s*)-(?:\s*)(\d+$)', row['data'])
            if(search):
                return "Wards %s" % (",".join([str(x) for x in range(int(search.group(1)), int(search.group(2))+1)]))
        elif row['type'] == 'comma':
            search = re.search(r'(\d+)((?:\s*),(?:\s*)*)', row['data'])
            return f"Wards {search.string}"
        elif row['type'] == 'single':
            search = re.search(r'(\d+$)', row['data'])
            return "Ward %d" % (int(search.group(1), 10))
        elif row['type'] == 'amp':
            search = re.search(r'(\d+)(?:\s*)&(?:\s*)(\d+$)', row['data'])
            return "Wards %d,%d" % (int(search.group(1)), int(search.group(2)))
        elif row['type'] == 'commahyphen':
            search = re.search(r'(\d+)((?:\s*),(?:\s*)*)', row['data'])
            return f"Wards {search.string}"
        elif row['type'] == 'unmatched':
            return converter(row['ReportingUnit'])
    except AttributeError:
        return converter(row['ReportingUnit'])
    
def TitleCaseReportingCounty(cnty):
    if cnty in ["La Crosse", "LA CROSSE"]:
        return "La_Crosse"
    if cnty in ["St. Croix", "ST.CROIX"]:
        return "St_Croix"
    tokens = cnty.split()
    cntyname = "_".join(tokens)
    return cntyname.title()

def ConvertRow(row):
    x = re.search(r'(^\D+)', row)
    pos = row.find('Ward')
    return row[:pos].strip()    

def TitleCaseReportingMcd(row):
    """
    Converts the CTV code and MCD_NAME from a row into a title-cased string
    representing a municipal designation.

    Args:
    row: A dictionary-like object with keys 'CTV' and 'MCD_NAME'. 
         'CTV' indicates the type of municipal designation ('C', 'T', 'V'),
         and 'MCD_NAME' is the name of the municipality.

    Returns:
    A string that combines the full municipal designation (e.g., "City of",
    "Town of", "Village of") with the title-cased MCD_NAME.

    Raises:
    Exception: If the 'CTV' value is not one of the expected options ('C', 'T', 'V').
    """
    ctv = ""
    if row['CTV'] == 'C':
        ctv = 'City of '
    elif row['CTV'] == 'T':
        ctv = 'Town of '
    elif row['CTV'] == 'V':
        ctv = 'Village of '
    else:
        raise Exception("Unexpected CTV option")

    return f"{ctv}{row['MCD_NAME'].title()}"

def partial_fips(row):
    return("%s%s" % (row['CNTY_FIPS'], '{0:05d}'.format(int(row['COUSUBFP']))))     

def ExpandFips(row):
    """
    Expands the FIPS codes for each ward within a municipality into a 
    concatenated string of full FIPS codes.

    Args:
    row: A dictionary-like object containing keys 'Wards' and 'MCD_FIPS'.
         'Wards' is a string that represents ward numbers, which may be 
         separated by commas, and 'MCD_FIPS' is the municipal FIPS code.

    Returns:
    A string where each ward number is combined with the 'MCD_FIPS' to 
    form a full FIPS code, with each full FIPS code separated by a pipe ('|') character.

    Raises:
    Prints the 'Wards' value if it cannot be split into a ward list.
    """
    fipslist = []
    if row['Wards'] and row['MCD_FIPS'] != '0':  
        try:  
            (_, wardsstr) = row['Wards'].split()
            wardlist = [x for x in wardsstr.split(',')]
        except:
            wardlist = [row['Wards']]
        fipslist = "|".join(["%s%s" % (row['MCD_FIPS'], x.rjust(4,'0')) for x in wardlist])
        return fipslist   
    else:
        print('ExpandFips Error:',row.CNTY_NAME, row.MCD_NAME, row.MCD_FIPS, row.Wards, row.EXPANDEDGEOID)
        return None
    
## A WEC Election results report file, see https://elections.wi.gov/elections/election-results
## The election results are reported by reporting unit, which are supersets of wards. 
## They may involve single sheets or multiple sheets depending on the election and there will be some
## header information that needs to be skipped.

def CreateElectionData(target_counties, columns_to_keep, geocode_df, str_to_append, path, file, skiprows = 0, sheet_name = 'Sheet1'):
    df = InitializeDataFrames(path, file, remote_file=False, kwargs={'skiprows': skiprows, 'sheet_name': sheet_name})
    _, voter_df = PreprocessData(df, str_to_append, target_counties)
    # voter_df = voter_df[columns_to_keep]
    result = pd.concat([voter_df, voter_df['ReportingUnit'].apply(lambda s: pd.Series(ProcessReportingUnitString(s),dtype='object'))], axis=1)
    result['Wards'] = result.apply(ConvertWardFormat, args=(ConvertWardStrings,), axis=1)
    result['data'] = result['data'].astype(str)
    result['data'] = result['data'].fillna('None')
    result['MCD_NAME'] = result['ReportingUnit'].map(ConvertRow)
    result['MCD_FIPS'] = '0'
    ## result['WinNumber_53'] = (.53 * result['Total']).fillna(0).astype(int)
    
    result = SetIntersection(result, geocode_df[['Area_Name', 'County_Code']], left_on = 'CNTY_NAME', right_on = 'Area_Name').drop(columns = 'Area_Name')
    for row in geocode_df.itertuples():
        result.loc[(result['MCD_NAME'] == row.MCD_NAME) & (result['County_Code'] == row.County_Code), 'MCD_FIPS'] = row.GEOID
    result['MCD_FIPS'] = result['MCD_FIPS'].astype(np.int64).astype(str)
    result['EXPANDEDGEOID'] = result.apply(ExpandFips, axis = 1)
    result = result[columns_to_keep]
    return result    

def compute_ward(ward):
    lst = ward.split(' ')
    return lst[0].zfill(4) if len(lst) == 1 else lst[-1].zfill(4)

def CreateVoterRegistrationData(target_counties, columns_to_keep, fips_dict, geocode_df, path, file, skiprows = 0):
    df = InitializeDataFrames(path, file, remote_file=False, kwargs = {'skiprows': skiprows})

    df = df[df['County'].isin(target_counties)].reset_index(drop=True)
    df['CNTY_NAME'] = df['County'].str.replace(" COUNTY", "").str.title()
    df['Muni'] = df['Muni'].str.split('-').str[0].str.strip().str.title()
    df['Muni'] = df['Muni'].str.replace("Of","of")
    df.rename(columns={'Muni': 'MCD_NAME'}, inplace=True)
    df['Ward'] = df['ward'].apply(lambda x: compute_ward(x))

    df['CNTY_FIPS'] = df['CNTY_NAME'].map(fips_dict)
    df['County_Code'] = df['CNTY_FIPS'].str[-3:]
    df['MCD_FIPS'] = '0'

## Test both the MCD name and the county code because there are a number of cases where names are duplicated across counties
    for row in geocode_df.itertuples():
        name = row.MCD_NAME.strip()
        code = row.County_Code.zfill(3)
        id = row.GEOID
        df.loc[((df['MCD_NAME'].str.strip() == name) & 
                (df['County_Code'].str.strip() == code)), 'MCD_FIPS'] = id
     
    df['GEOID'] = df['MCD_FIPS'] + df['Ward']
    df['GEOID'] = df['GEOID'].astype(str)
    df = df[columns_to_keep]
    df.reset_index(inplace=True, drop=True)
    return df

def TestRegex():
    """
    Test regular expressions supplied by "Bard AI" against samples that represent the data to be parsed.
    """
    regexpn = r"((?:^\D+)(?P<hypen>(\d+)(?:\s*)-(?:\s*)(\d+$)))|((?:^\D+)(?P<single>(\d+$)))|((?:^\D+)(?P<amp>(\d+)(?:\s*)&(?:\s*)(\d+$)))|((?:^\D+)(?P<comma>(\d+)(?:,\d+)*))"
    regexpn2 = r"([-,]+.*[-,]+)"
    regexpn3 = r"(,.*-)|(-.*,)"
    string1 = 'foo bar bazz 1,2,3,4'
    string2 = 'foo bar bazz 1-3,5-7,9'
    string3 = 'foo bar bazz 1-3,5-7'
    string4 = 'foo bar bazz 1-3'
    string5 = 'foo bar bazz 1'
    string6 = 'foo bar bazz 1,2'
    x = re.search(regexpn3, string2)
    if x is not None:
    # print(x.group('comma'), type(x.group('comma')))
        print(extract_numbers(string2))
    else: print('no luck for you!')        