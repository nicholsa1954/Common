import pandas as pd
import geopandas as gpd
import geojson
import pathlib
from pathlib import Path
import time, datetime
from datetime import date, datetime, timedelta, timezone
import sys, os
from typing import IO
from testVPNConnection import testVPNConnection

def InitializeGeoDataFrames(path, data_file, remote_file = True, kwargs={}):
	"""
	InitializeGeoDataFrames is a function that initializes and returns a GeoDataFrame object by loading data from a file.

	Parameters:
	- path (str): The path to the directory where the data file is located.
	- data_file (str): The name of the data file.
	- remote_file (bool): A flag indicating whether the data file is located remotely or not. Defaults to True.
	- kwargs (dict): Additional keyword arguments to be passed to the underlying read_file method.

	Returns:
	- gdf (GeoDataFrame): The initialized GeoDataFrame object containing the loaded data.

	If the remote_file flag is set to True and a VPN connection cannot be established using the testVPNConnection function, then an empty DataFrame is returned.
	If the path specified does not exist, an empty GeoDataFrame is returned.
	If the data file specified does not exist, an empty DataFrame is returned. The user may be prompted to enter network credentials.
	The function first checks the file extension of the data file. If the extension is '.shp', the data is read using the read_file method with the specified kwargs. Otherwise, an 'unknown file type' message is printed, and an empty GeoDataFrame is returned.
	The function also measures the time taken to load the geodata and prints the elapsed time.

	Note: This function requires the geopandas library to be installed.

	Example usage:
	InitializeGeoDataFrames('/path/to/data', 'data.shp', remote_file=True)
	"""    
	if remote_file and not testVPNConnection():
		print('Returning empty DataFrame.')
	if not Path(path).exists():
		print("Can't find the path:", path, "...")
		print('Returning empty GeoDataFrame.')
		return gpd.GeoDataFrame()
	inFile = Path(path + data_file)
	if not inFile.is_file():
		print('Cant find the file:', inFile, '-- returning empty DataFrame.')
		print('Do you need to enter network credentials?')
		return gpd.GeoDataFrame()
	print('Loading data from file...')
	
	sfx = pathlib.Path(data_file).suffix
	start_time = time.time()
	if sfx == '.shp':
		gdf = gpd.read_file(inFile, typ = 'series', orient = 'records', **kwargs)
	else:
		print('unknown file type:', sfx)
		return GeoDataFrame()
	elapsed_time = time.time() - start_time 
	print('Geodata loaded, elapsed time:', 
		time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
	return gdf       

def ComputeRegionCentroids(gdf):
	"""
	Compute the centroids of the regions in the given GeoDataFrame.

	Parameters:
	- gdf (GeoDataFrame): The input GeoDataFrame containing the regions.

	Returns:
	- focal_point (list): A list containing the latitude and longitude coordinates of the focal point.
	- gdf (GeoDataFrame): The modified input GeoDataFrame with additional columns for latitude and longitude.

	Note:
	- The input GeoDataFrame must have a valid coordinate reference system.
	- The input GeoDataFrame will be modified in place.
	"""    
	# Make sure we're using the correct coordinate reference system 
	gdf.to_crs('epsg:3035', inplace=True)
	gdf['Center_point'] = gdf['geometry'].centroid
	gdf['Center_point'] = gdf['Center_point'].to_crs('epsg:4326')
	gdf.to_crs('epsg:4326', inplace=True)

	# We want to figure the center point of the geometry so we can focus the visualization there
	focal_point = [
		gdf['Center_point'].y.mean(),
		gdf['Center_point'].x.mean()
	]

	idx = list(gdf.columns).index('geometry')
	gdf.insert(idx, "lat",
		gdf.Center_point.map(lambda p: p.y), True)
	gdf.insert(idx + 1, "lon",
		gdf.Center_point.map(lambda p: p.x), True)

	# Don't need it any more
	gdf.drop('Center_point', axis=1, inplace=True)    
	
	return focal_point, gdf
	
	
### on the 6933 crs see 
### https://gis.stackexchange.com/questions/218450/getting-polygon-areas-using-geopandas (at the bottom)
def ComputeAreaInKMSq(gdf):
	"""
	Compute the area in square kilometers of a GeoDataFrame.

	Parameters:
	- gdf: A GeoDataFrame object representing the geometry data.

	Returns:
	- float: The computed area in square kilometers.
	"""
	df = gdf.copy(deep=True)
	df = df.to_crs('epsg:6933')
	areaInKMSq = df['geometry'].area / 10**6
	return float(areaInKMSq.iloc[0])    
	
	
def GetCountyBounds(county_bounds_file:IO, county_name:str):
	"""
	GetCountyBounds function retrieves the county bounds for a given county name.

	Parameters:
	- countyBoundsFile: An IO object representing the county bounds file.
	- county_name: A string representing the name of the county.

	Returns:
	- A list containing the county bounds GeoDataFrame, the county bounds GeoJSON, and the focal point.

	Raises:
	- FileNotFoundError: If the countyBoundsFile does not exist.

	"""
	if county_bounds_file.exists():
		gdf = gpd.read_file(county_bounds_file)
		gdf = gdf[gdf['COUNTY_NAM'] == county_name]
		focal_point, gdf = ComputeRegionCentroids(gdf)
		gdf['id'] = gdf['COUNTY_NAM']
		gdf['z_layer'] = 0
		gdf['temp'] = gdf['z_layer']
		gdf.to_crs('epsg:4326', inplace=True)
		outFile = pathlib.Path('./' + county_name + '_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)
		return [gdf, gjsn, focal_point]
	else:
		print(' '.join(['County boundary file',county_bounds_file,'not found!']))   
		
		
def GetBoundedGeometry(gdf, bounds, compute_focal_point = True):
	"""
	Calculate the bounded geometry of a GeoDataFrame within a given bounding box.

	Parameters:
	- gdf: The GeoDataFrame containing the geometry to be bounded.
	- bounds: The bounding box coordinates (xmin, ymin, xmax, ymax) to limit the geometry.
	- compute_focal_point: Boolean flag indicating whether to compute the focal point of the bounded geometry. Defaults to True.

	Returns:
	- focal_point: A list of points representing the focal point of the bounded geometry, if compute_focal_point is True.
	- gdf: The GeoDataFrame with the bounded geometry.

	Note:
	- The function first calculates the area of the bounding box using the ComputeAreaInKMSq() function.
	- It then filters out any slivers of districts where the area of the sliver is less than 0.1% of the area of the boundary.
	- If the crs of the GeoDataFrame is None, it is set to 'epsg:4326'.
	- The function overlays the geometry of the GeoDataFrame with the boundary geometry, keeping only the intersecting parts.
	- The function also converts the geometry coordinates to 'epsg:4326' and calculates the area in square kilometers.
	- The resulting GeoDataFrame is further filtered based on the area cutoff.
	- If compute_focal_point is True, the function computes the focal point of the bounded geometry using the ComputeRegionCentroids() function.
	- The 'DISTRICT' column is stripped of leading zeros and the resulting GeoDataFrame is returned with only the 'DISTRICT', 'lat', 'lon', and 'geometry' columns.
	"""
	boundsArea = ComputeAreaInKMSq(bounds)

	### ignore slivers of districts where the area of the sliver is less than .1%
	### of the area of the boundary
	areaCutoff = boundsArea * .001
 
 	#TODO: think about this, it's very expensive on a big gdf
	if gdf.crs is None:
		gdf.crs = 'epsg:4326'
		
	gdf.to_crs('epsg:4326', inplace=True)

	#Overlay the geometry only, you don't want other data from the bounds
	#merged into your target gdf
	gdf = gpd.overlay(gdf, bounds[['geometry']], how='intersection')
	temp = gdf.copy(deep=True)
	temp.to_crs('epsg:6933', inplace=True)
	gdf['areaKMSq'] = temp['geometry'].area / 10**6
	gdf = gdf[gdf['areaKMSq'].gt(areaCutoff)]
	focal_point = []
	if compute_focal_point:
		[focal_point, gdf] = ComputeRegionCentroids(gdf)

	gdf['DISTRICT'] = gdf['DISTRICT'].map(lambda x: x.lstrip('0'))
	gdf = gdf[['DISTRICT', 'lat', 'lon', 'geometry']]
	return [focal_point, gdf]
		
		
def GetCountyBoardDistrictsInCounty(county_bounds_file:IO, county_name:str):
	"""
	Get the county board districts in a specific county.

	Parameters:
	- county_bounds_file: A file object representing the county bounds file.
	- county_name: A string representing the name of the county.

	Returns:
	- A list containing two elements:
		- gdf: A GeoDataFrame object representing the county board districts.
		- gjsn: A GeoJSON object representing the county board districts.

	If the county bounds file exists, the function reads the file and filters the data to include only the county with the specified name. It then renames a column and computes the centroids of the regions. Next, it saves the GeoDataFrame to a GeoJSON file and loads the GeoJSON data into a variable. Finally, it removes the GeoJSON file and returns the GeoDataFrame and GeoJSON objects as a list.

	If the county bounds file does not exist, the function prints an error message.
	"""    
	if county_bounds_file.exists():
		gdf = gpd.read_file(county_bounds_file)
		gdf = gdf.loc[gdf['CNTY_NAME'] == county_name]
		gdf = gdf.rename(columns={"SUPER": 'DISTRICT'})
		_, gdf = ComputeRegionCentroids(gdf)
		outFile = pathlib.Path('./' + county_name + '_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['County board district file',county_bounds_file,'not found!'])) 

def GetCountyBoardDistrictByNumber(county_bounds_file:IO, county_name:str, district_number:int):
    """
    Retrieves the county board district based on the county name and district number.

    Parameters:
    - county_bounds_file (IO): The file object representing the county bounds file.
    - county_name (str): The name of the county.
    - district_number (int): The district number.

    Returns:
    - gdf (GeoDataFrame): The GeoDataFrame containing the county board district information.
    - gjsn (GeoJSON): The GeoJSON representation of the county board district.

    Raises:
    - TypeError: If an error occurs when writing the GeoDataFrame to the output file.
    """    
	if county_bounds_file.exists():
		[gdf, _] = GetCountyBoardDistrictsInCounty(county_bounds_file, county_name)
		gdf = gdf.loc[gdf.DISTRICT == str(district_number)]
		outFile = pathlib.Path('./' + county_name + '_dist.geojson')
		try:
			gdf.to_file(outFile, driver='GeoJSON')
		except TypeError as e:
			print(e)
			pass
		with open(outFile) as f:
			gjsn = geojson.load(f)  
		os.remove(outFile)             
		return [gdf, gjsn]
	else:
		print(' '.join(['County board district file', str(county_bounds_file),'not found!']))  

def GetAssemblyDistrictsInCounty(assembly_districts_file:IO, county_bounds_file:IO, county_name:str):
	"""
	GetAssemblyDistrictsInCounty function retrieves the assembly districts in a specific county.

	Parameters:
	- assembly_districts_file: A file object that represents the assembly districts file.
	- county_bounds_file: A file object that represents the county bounds file.
	- county_name: A string that represents the name of the county.

	Returns:
	- A list containing two elements:
		1. A GeoDataFrame (gdf) object representing the assembly districts within the county bounds.
		2. A GeoJSON (gjsn) object representing the assembly districts within the county bounds.

	If the files assembly_districts_file and county_bounds_file exist, the function proceeds with the following steps:
	1. Get the county bounds using the GetCountyBounds function.
	2. Read the assembly districts file using gpd.read_file.
	3. Rename the 'ASM2021' column to 'DISTRICT' in the GeoDataFrame.
	4. Get the bounded geometry using the GetBoundedGeometry function.
	5. Rename the 'DISTRICT' column to 'id' in the GeoDataFrame.
	6. Add a 'z_layer' column with a default value of 0 to the GeoDataFrame.
	7. Save the GeoDataFrame to a GeoJSON file.
	8. Load the GeoJSON file using the geojson.load function.
	9. Remove the GeoJSON file.
	10. Return the GeoDataFrame and GeoJSON objects.

	If the files assembly_districts_file and county_bounds_file do not exist, the function prints a message indicating that the assembly district file was not found.
	"""    
	if assembly_districts_file.exists() and county_bounds_file.exists():
		[countyBounds, _, _] = GetCountyBounds(county_bounds_file, county_name)       
		gdf = gpd.read_file(assembly_districts_file)
		gdf = gdf.rename(columns={"ASM2021": 'DISTRICT'})
		_, gdf = GetBoundedGeometry(gdf, countyBounds)
		gdf = gdf.rename(columns={"DISTRICT": 'id'})
		gdf['z_layer'] = [0]*len(gdf)
		outFile = pathlib.Path('./assy_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)
		return [gdf, gjsn]
	else:
		print(' '.join(['Assembly district file', assembly_districts_file, 'not found!'])) 

def GetAssemblyDistrictsInBounds(assembly_districts_file:IO, bounds_gdf):	
	"""
	Given an assembly_districts_file and bounds_gdf, this function reads the assembly_districts_file, filters the data based on the bounds_gdf, and returns the filtered data as a GeoDataFrame and a GeoJSON object.

	Parameters:
	- assembly_districts_file (IO): The input file containing the assembly districts data.
	- bounds_gdf: The bounding GeoDataFrame used to filter the assembly districts data.

	Returns:
	- A list containing the filtered assembly districts data as a GeoDataFrame and a GeoJSON object.

	Note:
	- The function assumes that the assembly_districts_file exists in the file system.
	- If the assembly_districts_file does not exist, an error message will be printed.
	"""
	if assembly_districts_file.exists():
		gdf = gpd.read_file(assembly_districts_file)
		gdf = gdf.rename(columns={"ASM2021": 'DISTRICT'})
		_, gdf = GetBoundedGeometry(gdf, bounds_gdf)
		gdf = gdf.rename(columns={"DISTRICT": 'id'})
		gdf['z_layer'] = [0]*len(gdf)
		outFile = pathlib.Path('./assy_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)
		return [gdf, gjsn]
	else:
		print(' '.join(['Assembly district file', assembly_districts_file, 'not found!'])) 		
		
		

def GetSenateDistrictsInCounty(senate_districts_file:IO, county_bounds_file:IO, county_name):
	"""
	Get the Senate districts within a county.

	Parameters:
	- senate_districts_file: The file containing the Senate districts data. Must be a valid file path.
	- county_bounds_file: The file containing the county bounds data. Must be a valid file path.
	- county_name: The name of the county.

	Returns:
	- A list containing the filtered Senate district data as a GeoDataFrame and GeoJSON.

	If both the `senate_districts_file` and `county_bounds_file` exist, the function reads the county bounds data and filters the Senate districts data based on the county bounds. It renames the columns of the filtered data and adds additional columns. The filtered data is then saved as a GeoJSON file and loaded as a GeoJSON object. Finally, the function returns the filtered data as a GeoDataFrame and the GeoJSON object.

	If either the `senate_districts_file` or `county_bounds_file` does not exist, the function displays an error message.
	"""    
	if senate_districts_file.exists() and county_bounds_file.exists():
		[countyBounds, _, _] = GetCountyBounds(county_bounds_file, county_name)    
		gdf = gpd.read_file(senate_districts_file)
		gdf = gdf.rename(columns={"SEN2021": 'DISTRICT'})
		_, gdf = GetBoundedGeometry(gdf, countyBounds)
		gdf = gdf.rename(columns={"DISTRICT": 'id'})
		gdf['z_layer'] = [0]*len(gdf)
		gdf['temp'] = gdf['z_layer']		
		outFile = pathlib.Path('./sen_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['Senate district file', senate_districts_file, 'not found!']))  

def GetSenateDistrictsInBounds(senate_districts_file:IO, bounds_gdf,):	
	if senate_districts_file.exists():
		gdf = gpd.read_file(senate_districts_file)
		gdf = gdf.rename(columns={"SEN2021": 'DISTRICT'})
		_, gdf = GetBoundedGeometry(gdf, bounds_gdf)
		gdf = gdf.rename(columns={"DISTRICT": 'id'})
		gdf['z_layer'] = [0]*len(gdf)
		outFile = pathlib.Path('./sen_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['Senate district file', senate_districts_file, 'not found!']))  

	

def GetAldermanicDistrictsInCity(aldermanic_districts_file:IO, county_bounds_file:IO, county_name:str, city_name:str):
	"""
	GetAldermanicDistrictsInCity is a function that takes in four parameters:
	
	1. aldermanic_districts_file:IO - a file object that represents the aldermanic districts file.
	2. county_bounds_file:IO - a file object that represents the county bounds file.
	3. county_name:str - a string that represents the name of the county.
	4. city_name:str - a string that represents the name of the city.
	
	This function reads the aldermanic districts file and filters the data based on the county name and city name.
	If the filtered dataset is empty, it prints an error message and returns None, None.
	Otherwise, it renames a column in the dataset, performs further processing based on the county bounds, and saves the result to a GeoJSON file.
	The function then loads the GeoJSON file, removes it, and returns the processed dataset and the loaded GeoJSON as a list.
	If the aldermanic districts file does not exist, it prints a file not found error message.
	"""    
	if aldermanic_districts_file.exists():
		[countyBounds, _] = GetCountyBounds(county_bounds_file, county_name)         
		gdf = gpd.read_file(aldermanic_districts_file)
		gdf = gdf.loc[(gdf.CNTY_NAME == county_name) & (gdf.MCD_NAME == city_name)]
	
		if gdf.empty:
			print (' '.join(['error -- file has no city with name', city_name, 'in county with name', county_name]))
			return None, None
		else:
			gdf = gdf.rename(columns={'ALDER': 'DISTRICT'})
			_, gdf = GetBoundedGeometry(gdf, countyBounds)
			outFile = pathlib.Path('./' + county_name + '_gdf.geojson')
			gdf.to_file(outFile, driver='GeoJSON')
			with open(outFile) as f:
				gjsn = geojson.load(f)
			os.remove(outFile)
			return [gdf, gjsn]
	else:
		print(' '.join(['Aldermanic district file', aldermanic_districts_file, 'not found!'])) 
		
		
def GetPublicSchoolDistrictsInCounty(school_districts_file:IO, county_bounds_file, county_name:str, city_name:str):
		"""
		GetPublicSchoolDistrictsInCounty retrieves the public school districts in a specific county and city.

		Parameters:
		- school_districts_file: The file containing the school districts data. (IO)
		- county_bounds_file: The file containing the county bounds data.
		- county_name: The name of the county.
		- city_name: The name of the city.

		Returns:
		- A list containing the geopandas dataframe (gdf) and the geojson (gjsn) representation of the school districts in the specified county and city.
		- If the file does not exist, prints an error message and returns None, None.
		"""    
		if school_districts_file.exists():
			[countyBounds, _] = GetCountyBounds(county_bounds_file, county_name)         
			gdf = gpd.read_file(school_districts_file)
			gdf = gdf.loc[gdf.DISTRICT == city_name]
			
			if gdf.empty:
				print (' '.join(['error -- file has no city with name', city_name, 'in county with name', county_name]))
				return None, None
			else:
				_, gdf = GetBoundedGeometry(gdf, countyBounds)
				outFile = pathlib.Path('./' + county_name + '_gdf.geojson')
				gdf.to_file(outFile, driver='GeoJSON')
				with open(outFile) as f:
					gjsn = geojson.load(f)
				os.remove(outFile)
				return [gdf, gjsn]
		else:
			print(' '.join(['School district file', school_districts_file, 'not found!']))         

def GetAldermanicDistrictByNumber(aldermanic_districts_file:IO, county_bounds_file:IO, county_name:str, city_name:str, district_number:int):
	"""
	GetAldermanicDistrictByNumber finds and returns the aldermanic district information for a specific district number in a given city and county.

	:param aldermanic_districts_file: File object pointing to the aldermanic districts file.
	:type aldermanic_districts_file: IO
	:param county_bounds_file: File object pointing to the county bounds file.
	:type county_bounds_file: IO
	:param county_name: Name of the county.
	:type county_name: str
	:param city_name: Name of the city.
	:type city_name: str
	:param district_number: The number of the aldermanic district to retrieve information for.
	:type district_number: int
	:return: A list containing two elements - a GeoDataFrame object containing the aldermanic district information for the specified district number, and a GeoJSON object representing the same information.
	:rtype: list
	"""    
	if aldermanic_districts_file.exists() and county_bounds_file.exists():
		[gdf, _] = GetAldermanicDistrictsInCity(aldermanic_districts_file, county_bounds_file, county_name, city_name)
		gdf = gdf.loc[gdf.DISTRICT == str(district_number)]
		outFile = pathlib.Path('./' + city_name + '_dist.geojson')
		try:
			gdf.to_file(outFile, driver='GeoJSON')
		except TypeError as e:
			print(e)
			pass
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)             
		return [gdf, gjsn]
	else:
		print(' '.join(['Aldermanic district file',aldermanic_districts_file,'not found!']))  
		
def GetWardsInCounty(ward_bounds_file:IO, county_name:str):
	"""
	GetWardsInCounty function retrieves the wards in a specific county.

	Parameters:
	- ward_bounds_file: A file object representing the ward bounds file. It should be of type IO.
	- county_name: A string representing the name of the county.

	Returns:
	- A list containing two elements:
		- gdf: A GeoDataFrame object representing the wards in the specified county.
		- gjsn: A GeoJSON object representing the wards in the specified county.

	"""    
	if ward_bounds_file.exists():
		gdf = gpd.read_file(ward_bounds_file)
		gdf = gdf.loc[gdf['CNTY_NAME'] == county_name]
		_, gdf = ComputeRegionCentroids(gdf)
		gdf['STR_WARDS'] = gdf['STR_WARDS'].apply(lambda x : x.lstrip('0'))
		gdf['id'] = gdf['LABEL']
		gdf['temp'] = 0
		gdf.to_crs('epsg:4326', inplace = True)    
		outFile = pathlib.Path('./' + county_name + '_gdf.geojson')
		gdf[['id', 'geometry']].to_file(outFile, driver='GeoJSON')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['Ward boundary file',countyBoundsFile,'not found!'])) 

def GetWardsInCity(ward_bounds_file:IO, city_name:str):
	"""
	GetWardsInCity is a function that takes in two parameters: ward_bounds_file of type IO and city_name of type str. This function reads the ward_bounds_file and filters the data based on the city_name. It then computes the centroids of the regions and removes leading zeros from the 'STR_WARDS' column. The function converts the data to the 'epsg:4326' coordinate system and saves it to a GeoJSON file. It then loads the GeoJSON file and removes it. Finally, the function returns a list containing two elements: gdf and gjsn.

	Parameters:
	- ward_bounds_file (IO): The file object representing the ward bounds file.
	- city_name (str): The name of the city.

	Returns:
	- list: A list containing two elements: gdf and gjsn.
	"""    
	if ward_bounds_file.exists():
		gdf = gpd.read_file(ward_bounds_file)
		gdf = gdf.loc[gdf['MCD_NAME'] == city_name]
		_, gdf = ComputeRegionCentroids(gdf)
		gdf['STR_WARDS'] = gdf['STR_WARDS'].apply(lambda x : x.lstrip('0'))
		gdf['id'] = gdf['STR_WARDS']
		gdf['temp'] = 0
		gdf.to_crs('epsg:4326', inplace = True)           
		outFile = pathlib.Path('./' + county + '_gdf.geojson')
		gdf[['id', 'geometry']].to_file(outFile, driver='GeoJSON')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['Ward boundary file', ward_bounds_file,'not found!']))  

def GetCityWardByNumber(ward_bounds_file:IO, city_name:str, ward_number:int):
	"""
	This function retrieves the city ward information based on a given ward number.
	
	Parameters:
	- ward_bounds_file (IO): A file object representing the ward bounds file.
	- city_name (str): The name of the city.
	- ward_number (int): The ward number to retrieve information for.
	
	Returns:
	- list: A list containing two elements. The first element is a GeoDataFrame object containing the ward information. The second element is a GeoJSON object representing the ward geometry.
	"""    
	if ward_bounds_file.exists():
		gdf = gpd.read_file(ward_bounds_file)
		gdf = gdf.loc[gdf['MCD_NAME'] == city_name]
		gdf['STR_WARDS'] = gdf['STR_WARDS'].apply(lambda x : x.lstrip('0'))
		gdf = gdf.loc[gdf['STR_WARDS'] == str(ward_number)]
		_, gdf = ComputeRegionCentroids(gdf)        
		outFile = pathlib.Path('./' + city_name + '_gdf.geojson')
		gdf[['STR_WARDS', 'geometry']].to_file(outFile, driver='GeoJSON')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['Ward boundary file',ward_bounds_file,'not found!']))   
		
def GetCityInCounty(county_ward_gdf, city_name):
    	"""
	Given a GeoDataFrame and a city name, this function extracts the data for the specified city from the GeoDataFrame and saves it as a GeoJSON file. The function takes two parameters:
	- `county_ward_gdf`: A GeoDataFrame containing data for all counties and wards.
	- `city_name`: The name of the city for which the data needs to be extracted.

	The function performs the following steps:
	1. Filters the `county_ward_gdf` to get the data for the specified `city_name`.
	2. Creates a new GeoDataFrame with the filtered data.
	3. Adds additional columns (`id`, `z_layer`, `temp`) to the new GeoDataFrame.
	4. Saves the new GeoDataFrame as a GeoJSON file.
	5. Reads the saved GeoJSON file using the `geojson` library.
	6. Removes the saved GeoJSON file.
	7. Returns a list containing the new GeoDataFrame and the loaded GeoJSON data.

	Note: The `county_ward_gdf` parameter should have a column named `MCD_NAME` which contains the city names.

	:param county_ward_gdf: A GeoDataFrame containing data for all counties and wards.
	:param city_name: The name of the city for which the data needs to be extracted.
	:return: A list containing a GeoDataFrame and the loaded GeoJSON data.
	"""
	gdf = county_ward_gdf.loc[county_ward_gdf.MCD_NAME == city_name].copy(deep = True)
	gdf = gpd.GeoDataFrame( geometry = gpd.GeoSeries(gdf.unary_union))
	gdf['id'] = city_name
	gdf['z_layer'] = [0]*len(gdf)
	gdf['temp'] = gdf['z_layer']

	outFile = pathlib.Path('./' + city_name + '_bounds.geojson')
	gdf.to_file(outFile, driver='GeoJSON')
	with open(outFile) as f:
		gjsn = geojson.load(f) 

	os.remove(outFile)
	return [gdf, gjsn]

def ComputeIdForMapLabel(row):
	return ' '.join([row['CTV'], row['MCD_NAME'], 'Ward', row['WARDID']])
	
def GetWardDataFromLTSBFile(inFile:IO, county_name, headers, numeric, geometry, vap_multiplier = 2.0, write_Excel = False):
	"""
	Reads data from a LTSB file and extracts specific ward data for a given county.

	:param inFile: The input file to read data from.
	:type inFile: IO
	:param county_name: The name of the county to filter the data for.
	:type county_name: any
	:param headers: The list of column headers to include in the output.
	:type headers: list
	:param numeric: The list of numeric column names to include in the output.
	:type numeric: list
	:param geometry: The list of geometry column names to include in the output.
	:type geometry: list
	:param vap_multiplier: The multiplier to determine the target ward cutoff based on mean Latinx VAP. Default is 2.0.
	:type vap_multiplier: float
	:param write_Excel: Whether to write the output to an Excel file. Default is False.
	:type write_Excel: bool
	:return: A list containing the target ward cutoff, a list of ward IDs, a list of population IDs, a focal point, a GeoDataFrame, and a GeoJSON object.
	:rtype: list
	"""    
	if inFile.exists():
		gdf = gpd.read_file(inFile)
		print('number of wards in state:', len(gdf))
		gdf = gdf.loc[gdf['CNTY_NAME'] == county_name]

		print('number of wards in', county_name, 'county:', len(gdf))

		gdf = gdf[headers + numeric + geometry]

		# Do a little renaming
		gdf.rename(columns = {'PERSONS':'Total', 'PERSONS18':'VAP', 
			'HISPANIC':'LATINX', 'HISPANIC18':'LATINX18'}, 
			inplace = True)

		gdf.rename(columns = {'WHITE18':'WhiteVAP','BLACK18':'BlackVAP',
			'LATINX18':'LatinxVAP','ASIAN18':'AsianVAP'}, 
			inplace = True)

		gdf['GEOID'] = gdf['GEOID'].astype(str)
		gdf['WARDID'] = gdf['WARDID'].astype(str)
		gdf['WARDID'] = gdf['WARDID'].apply(lambda x : x[-4:].lstrip('0'))
		gdf['id'] = gdf.apply(lambda row : ComputeIdForMapLabel(row), axis = 1)
		gdf['z_layer'] = [0]*len(gdf)
		gdf['temp'] = gdf['z_layer']

		temp = gdf.sort_values(by = ['LatinxVAP'], ascending = False)
		pop_list = list(temp['GEOID'][0:5])
		ward_list = list(temp['WARDID'][0:5])
		mean_latinx_vap = int(temp['LatinxVAP'].mean())
		target_ward_cutoff = vap_multiplier * mean_latinx_vap
		temp = temp.loc[temp['LatinxVAP'] >= target_ward_cutoff]
 
		id_list = list(temp['GEOID'])
		int_list = sorted(id_list, key = int)
		print('mean latinx VAP:', mean_latinx_vap)
		print('target_ward_cutoff:', target_ward_cutoff)
		# print('key wards:', int_list)
		# print('key wards:', sorted(list(temp['WARDID'].astype(int)) ))
		# print(temp[['WARDID','LatinxVAP']].head(len(temp)))
		
		_, gdf = ComputeRegionCentroids(gdf)
		focal_point, _ = ComputeRegionCentroids(temp)        

		# Compute values for voting age population percentages
		idx = list(gdf.columns).index('AsianVAP') + 1    
		gdf.insert(idx, 'BlackVAPPct', gdf['BlackVAP'] / gdf['VAP'])
		gdf['BlackVAPPct'] = gdf['BlackVAPPct'].fillna(0)
		gdf['BlackVAPPct'] = gdf['BlackVAPPct'].map(
			lambda x: "{:.2f}".format(x))
		gdf['BlackVAPPct'] = gdf['BlackVAPPct'].astype(float)
		
		gdf.insert(idx+1, 'LatinxVAPPct', gdf['LatinxVAP'] / gdf['VAP'])
		gdf['LatinxVAPPct']= gdf['LatinxVAPPct'].fillna(0)
		gdf['LatinxVAPPct'] = gdf['LatinxVAPPct'].map(
			lambda x: "{:.2f}".format(x))
		gdf['LatinxVAPPct'] = gdf['LatinxVAPPct'].astype(float)

		gdf.insert(idx+2, 'AsianVAPPct', gdf['AsianVAP'] / gdf['VAP'])
		gdf['AsianVAPPct'] = gdf['AsianVAPPct'].fillna(0)
		gdf['AsianVAPPct'] = gdf['AsianVAPPct'].map(
			lambda x: "{:.2f}".format(x))
		gdf['AsianVAPPct'] = gdf['AsianVAPPct'].astype(float)
			
		gdf.reset_index(inplace = True)
		
		outFile = pathlib.Path('./' + county_name + '_population.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f) 

		os.remove(outFile)
		
		if write_Excel:
			parent = inFile.parent
			outFile = parent.joinpath(''.join(['Local_Redistricting_', county_name,'Wards-shp.xlsx']))
			gdf.to_excel(outFile)

		return [target_ward_cutoff, id_list, ward_list, pop_list, focal_point, gdf, gjsn]

	else:
		print('ltsb 2021 data file not found')
		
		
def GetTargetWardsInBounds(gdf, target_ward_cutoff, write_Excel = False):
	"""
	Retrieves the target wards within the specified bounds from the given GeoDataFrame.

	Args:
		gdf (GeoDataFrame): The input GeoDataFrame.
		target_ward_cutoff (float): The threshold value for the LatinxVAP column.
		write_Excel (bool, optional): Flag indicating whether to write the result to an Excel file. Defaults to False.

	Returns:
		list: A list containing two elements:
			- gdf (GeoDataFrame): The filtered GeoDataFrame.
			- gjsn (GeoJSON): The GeoJSON representation of the filtered GeoDataFrame.
	"""
    county = gdf.iloc[0].CNTY_NAME
	gdf = gdf.loc[gdf['LatinxVAP'] >= target_ward_cutoff]
	gdf.reset_index(inplace = True)
	outFile = pathlib.Path('./_temp.geojson')
	gdf.to_file(outFile, driver='GeoJSON')
	with open(outFile) as f:
		gjsn = geojson.load(f) 
	os.remove(outFile)
	
	if write_Excel:
		county = gdf.iloc[0].CNTY_NAME
		parent = inFile.parent
		outFile = parent.joinpath(''.join([county,'TargetWards-shp.xlsx']))
		gdf.to_excel(outFile)
	return [gdf, gjsn]	
	
	
def GetPassiveWardsInBounds(gdf, target_ward_cutoff, write_Excel = False):
    """
    Get the passive wards in bounds.

    Parameters:
    - gdf: The GeoDataFrame containing the data.
    - target_ward_cutoff: The cutoff value for LatinxVAP.
    - write_Excel: Optional parameter indicating whether to write the data to an Excel file. Default is False.

    Returns:
    - A list containing the GeoDataFrame and the geojson representation of the data.
    """    
    county = gdf.iloc[0].CNTY_NAME
	gdf = gdf.loc[gdf['LatinxVAP'] < target_ward_cutoff]
	gdf.reset_index(inplace = True)
	outFile = pathlib.Path('./_temp.geojson')
	gdf.to_file(outFile, driver='GeoJSON')
	with open(outFile) as f:
		gjsn = geojson.load(f) 
	os.remove(outFile)
	
	if write_Excel:
		county = gdf.iloc[0].CNTY_NAME
		parent = inFile.parent
		outFile = parent.joinpath(''.join([county,'PassiveWards-shp.xlsx']))
		gdf.to_excel(outFile)
	return [gdf, gjsn]	
 