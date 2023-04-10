
import time
from datetime import datetime
import pandas as pd
import googlemaps

from empowerJSONhelpers import IsBlank as is_blank
from empowerJSONhelpers import IsNotBlans as is_not_blank

import configparser
config = configparser.ConfigParser()
config.read('C:/Users/nicho/Documents/VocesDeLaFrontera/Common/config.ini')
mapbox_access_token = config['mapbox']['secret_token']
basic_style = config['mapbox']['basic_style']

key = config['google']['map_key']
gmaps_key = googlemaps.Client(key=key)

# substituting the imports abor for these:
# def is_blank(myString):
    # if (isinstance(myString, float) | (isinstance(myString, int))): return True
    # if myString and myString.strip():
        ## myString is not None AND myString is not empty or blank
        # return False
    ## myString is None OR myString is empty or blank
    # return True
    
# def is_not_blank(myString):
    # if (isinstance(myString, float) | (isinstance(myString, int))): return False
    # if myString and myString.strip():
        ## myString is not None AND myString is not empty or blank
        # return True
    ## myString is None OR myString is empty or blank
    # return False    

def google_geocode(row, missed = 0):
    if is_blank(row.Address) or is_blank(row.City) or is_blank(row.State):
        missed += 1
        return pd.Series([])
    try:
        add = ', '.join([row.Address, row.City, row.State])
        g = gmaps_key.geocode(add)
    except TypeError:
        print(row['VANID'], row['Member Name'], row['Last Name'] )
        missed += 1
        return pd.Series([])     
    if g:
        lat = g[0]["geometry"]["location"]["lat"]
        lng = g[0]["geometry"]["location"]["lng"]
        return pd.Series([lat, lng])
    else:
        missed += 1
        return pd.Series([])

#### usage:        
## careful!  Expensive!!
# print('before geocode df shape is:',df.shape)
# print("begin: ", datetime.now().strftime("%H:%M:%S"))
# start = time.time()

## This will write out 2 series as 2 columns
## But be careful!  Expensive!
# df[['lat', 'lng']] = df.apply(lambda row : geocode(row), axis = 1)

# elapsed = time.time() - start
# print('locations missed:', missed)
# print(time.strftime("elapsed: %H:%M:%S", time.gmtime(elapsed)) )  



def nominatim_geocode(geocode, inputdf):
    df = inputdf.copy(deep = True)
    print('before geocode df shape is:',df.shape)
    start = time.time()
    print("begin: ", datetime.now().strftime("%H:%M:%S"))
    
    df['FullAddress'] = df['Address'] + ', ' + df['City'] + ', ' + df['State']
    df['gcode'] = df['FullAddress'].apply(geocode)
    df = df[(~df['gcode'].isnull())]  
    
    df['point'] = df['gcode'].apply(lambda loc: tuple(loc.point) if loc else None) 
    df[['latitude', 'longitude', 'altitude']] = pd.DataFrame(df['point'].tolist(), index=df.index) 
    df = df[(~df['latitude'].isna()) & (~df['longitude'].isna()) & (~df['altitude'].isna())]   
    df.drop(['gcode', 'point','altitude'], inplace=True, axis = 1) 
    df.reset_index(drop = True, inplace = True)  
    print('after geocode df shape is:',df.shape)    
    gdf = gpd.GeoDataFrame(df, geometry = gpd.points_from_xy(df.latitude, df.longitude))
    gdf.set_crs('epsg:4326', inplace = True)
    print('after conversion to geodataframe gdf shape is:', gdf.shape)
    elapsed = time.time() - start
    print(time.strftime("elapsed: %H:%M:%S", time.gmtime(elapsed)) )   
    return gdf
   
### usage:   
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter

# geolocator = Nominatim(user_agent = 'myGeolocator')
# geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# gc_gdf = geocodeAddresses(geocode, df)

# print('geocode done...')    