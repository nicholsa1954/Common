import numpy as np
import re
import sys
sys.path.append('../../Common')

from ward_mappings import ward_mappings
keys = ward_mappings.keys()

def PreprocessData(df, target_county_list):
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
    
    df.rename(columns={'Unnamed: 0': 'CNTY_NAME', 'Unnamed: 1': 'ReportingUnit', 'Unnamed: 2': 'Total', 'SCATTERING': 'Other'}, inplace=True)
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
    if numbers: return ','.join(map(str,numbers))
    return None

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
        if ward == 'County Totals:':
            pass
        elif ward == 'Office Totals:':
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
    startrow = row[0:pos]
    subrow = row[pos:len(row)]
    if subrow in keys:
        return ward_mappings[subrow]
    else:
        raise Exception(subrow, 'not in dictionary')
    
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
            return "Wards %s" % (search.string)
        elif row['type'] == 'single':
            search = re.search(r'(\d+$)', row['data'])
            return "Ward %d" % (int(search.group(1), 10))
        elif row['type'] == 'amp':
            search = re.search(r'(\d+)(?:\s*)&(?:\s*)(\d+$)', row['data'])
            return "Wards %d,%d" % (int(search.group(1)), int(search.group(2)))
        elif row['type'] == 'commahyphen':
            search = re.search(r'(\d+)((?:\s*),(?:\s*)*)', row['data'])
            return "Wards %s" % (search.string)
        elif row['type'] == 'unmatched':
            return converter(row['ReportingUnit'])    
    except AttributeError:
        return converter(row['ReportingUnit'])
    
def TitleCaseReportingCounty(cnty):
    if cnty == "La Crosse" or cnty == "LA CROSSE":
        return "La_Crosse"
    if cnty == "St. Croix" or cnty == "ST.CROIX":
        return "St_Croix"
    tokens = cnty.split()
    cntyname = "_".join(tokens)
    return cntyname.title()

def ConvertRow(row):
    x = re.search(r'(^\D+)', row)
    pos = row.find('Ward')
    startrow = row[0:pos].strip()
    return startrow    

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
        
    return("%s%s") %(ctv, row['MCD_NAME'].title())

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
    if row['Wards']:    
        try:  
            (_, wardsstr) = row['Wards'].split()
            wardlist = [x for x in wardsstr.split(',')]
        except:
            print(row['Wards'])
            wardlist = [row['Wards']]
        fipslist = "|".join(["%s%s" % (row['MCD_FIPS'], x.rjust(4,'0')) for x in wardlist])
    return fipslist   

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