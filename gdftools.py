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
	df = gdf.copy(deep=True)
	df = df.to_crs('epsg:6933')
	areaInKMSq = df['geometry'].area / 10**6
	return float(areaInKMSq.iloc[0])    
	
	
def GetCountyBounds(countyBoundsFile:IO, county:str):
	if countyBoundsFile.exists():
		gdf = gpd.read_file(countyBoundsFile)
		gdf = gdf[gdf['COUNTY_NAM'] == county]
		focal_point, gdf = ComputeRegionCentroids(gdf)
		gdf['id'] = gdf['COUNTY_NAM']
		gdf['z_layer'] = 0
		gdf['temp'] = gdf['z_layer']
		gdf.to_crs('epsg:4326', inplace=True)
		outFile = pathlib.Path('./' + county + '_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)
		return [gdf, gjsn, focal_point]
	else:
		print(' '.join(['County boundary file',countyBoundsFile,'not found!']))   
		
		
def GetBoundedGeometry(gdf, bounds, compute_focal_point = True):
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
	 
		
		
def GetCountyBoardDistrictsInCounty(countyBoundsFile:IO, county:str):
	if countyBoundsFile.exists():
		gdf = gpd.read_file(countyBoundsFile)
		gdf = gdf.loc[gdf['CNTY_NAME'] == county]
		gdf = gdf.rename(columns={"SUPER": 'DISTRICT'})
		_, gdf = ComputeRegionCentroids(gdf)
		outFile = pathlib.Path('./' + county + '_gdf.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['County board district file',countyBoundsFile,'not found!'])) 

def GetCountyBoardDistrictByNumber(countyBoundsFile:IO, county:str, dist_number:int):
	if countyBoundsFile.exists():
		[gdf, _] = GetCountyBoardDistrictsInCounty(countyBoundsFile, county)
		gdf = gdf.loc[gdf.DISTRICT == str(dist_number)]
		outFile = pathlib.Path('./' + county + '_dist.geojson')
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
		print(' '.join(['County board district file', str(countyBoundsFile),'not found!']))  

def GetAssemblyDistrictsInCounty(assemblyDistrictsFile:IO, countyBoundsFile:IO, county:str):
	if assemblyDistrictsFile.exists() and countyBoundsFile.exists():
		[countyBounds, _, _] = GetCountyBounds(countyBoundsFile, county)       
		gdf = gpd.read_file(assemblyDistrictsFile)
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
		print(' '.join(['Assembly district file', assemblyDistrictsFile, 'not found!'])) 

def GetAssemblyDistrictsInBounds(assemblyDistrictsFile:IO, bounds_gdf):	
	if assemblyDistrictsFile.exists():
		gdf = gpd.read_file(assemblyDistrictsFile)
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
		print(' '.join(['Assembly district file', assemblyDistrictsFile, 'not found!'])) 		
		
		

def GetSenateDistrictsInCounty(senateDistrictsFile:IO, countyBoundsFile:IO, county):
	if senateDistrictsFile.exists() and countyBoundsFile.exists():
		[countyBounds, _, _] = GetCountyBounds(countyBoundsFile, county)    
		gdf = gpd.read_file(senateDistrictsFile)
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
		print(' '.join(['Senate district file', senateDistrictsFile, 'not found!']))  

def GetSenateDistrictsInBounds(senateDistrictsFile:IO, bounds_gdf,):	
	if senateDistrictsFile.exists():
		gdf = gpd.read_file(senateDistrictsFile)
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
		print(' '.join(['Senate district file', senateDistrictsFile, 'not found!']))  

	

def GetAldermanicDistrictsInCity(aldermanicDistrictsFile:IO, countyBoundsFile:IO, county:str, city:str):
	if aldermanicDistrictsFile.exists():
		[countyBounds, _] = GetCountyBounds(countyBoundsFile, county)         
		gdf = gpd.read_file(aldermanicDistrictsFile)
		gdf = gdf.loc[(gdf.CNTY_NAME == county) & (gdf.MCD_NAME == city)]
	   
		if gdf.empty:
			print (' '.join(['error -- file has no city with name', city, 'in county with name', county]))
			return None, None
		else:
			gdf = gdf.rename(columns={'ALDER': 'DISTRICT'})
			_, gdf = GetBoundedGeometry(gdf, countyBounds)
			outFile = pathlib.Path('./' + county + '_gdf.geojson')
			gdf.to_file(outFile, driver='GeoJSON')
			with open(outFile) as f:
				gjsn = geojson.load(f)
			os.remove(outFile)
			return [gdf, gjsn]
	else:
		print(' '.join(['Aldermanic district file', aldermanicDistrictsFile, 'not found!'])) 
		
		
def GetPublicSchoolDistrictsInCounty(schoolDistrictsFile:IO, countyBoundsFile, county:str, city:str):
	if schoolDistrictsFile.exists():
		[countyBounds, _] = GetCountyBounds(countyBoundsFile, county)         
		gdf = gpd.read_file(schoolDistrictsFile)
		gdf = gdf.loc[gdf.DISTRICT == city]
		
		if gdf.empty:
			print (' '.join(['error -- file has no city with name', city, 'in county with name', county]))
			return None, None
		else:
			_, gdf = GetBoundedGeometry(gdf, countyBounds)
			outFile = pathlib.Path('./' + county + '_gdf.geojson')
			gdf.to_file(outFile, driver='GeoJSON')
			with open(outFile) as f:
				gjsn = geojson.load(f)
			os.remove(outFile)
			return [gdf, gjsn]
	else:
		print(' '.join(['Aldermanic district file', aldermanicDistrictsFile, 'not found!']))         

def GetAldermanicDistrictByNumber(aldermanicDistrictsFile:IO, countyBoundsFile:IO, county:str, city:str, dist_number:int):
	if aldermanicDistrictsFile.exists() and countyBoundsFile.exists():
		[gdf, _] = GetAldermanicDistrictsInCity(aldermanicDistrictsFile, countyBoundsFile, county, city)
		gdf = gdf.loc[gdf.DISTRICT == str(dist_number)]
		outFile = pathlib.Path('./' + city + '_dist.geojson')
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
		print(' '.join(['Aldermanic district file',aldermanicDistrictsFile,'not found!']))  
		
def GetWardsInCounty(wardBoundsFile:IO, county:str):
	if wardBoundsFile.exists():
		gdf = gpd.read_file(wardBoundsFile)
		gdf = gdf.loc[gdf['CNTY_NAME'] == county]
		_, gdf = ComputeRegionCentroids(gdf)
		gdf['STR_WARDS'] = gdf['STR_WARDS'].apply(lambda x : x.lstrip('0'))
		gdf['id'] = gdf['LABEL']
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
		print(' '.join(['Ward boundary file',countyBoundsFile,'not found!'])) 

def GetWardsInCity(wardBoundsFile:IO, city:str):
	if wardBoundsFile.exists():
		gdf = gpd.read_file(wardBoundsFile)
		gdf = gdf.loc[gdf['MCD_NAME'] == city]
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
		print(' '.join(['Ward boundary file',countyBoundsFile,'not found!']))  

def GetCityWardByNumber(wardBoundsFile:IO, city:str, ward_number:int):
	if wardBoundsFile.exists():
		gdf = gpd.read_file(wardBoundsFile)
		gdf = gdf.loc[gdf['MCD_NAME'] == city]
		gdf['STR_WARDS'] = gdf['STR_WARDS'].apply(lambda x : x.lstrip('0'))
		gdf = gdf.loc[gdf['STR_WARDS'] == str(ward_number)]
		_, gdf = ComputeRegionCentroids(gdf)        
		outFile = pathlib.Path('./' + city + '_gdf.geojson')
		gdf[['STR_WARDS', 'geometry']].to_file(outFile, driver='GeoJSON')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f)
		os.remove(outFile)            
		return [gdf, gjsn]
	else:
		print(' '.join(['Ward boundary file',countyBoundsFile,'not found!']))   
		
def GetCityInCounty(county_ward_gdf, city_name):
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
	
def GetWardDataFromLTSBFile(inFile:IO, county, headers, numeric, geometry, vap_multiplier = 2.0, write_Excel = False):
	if inFile.exists():
		gdf = gpd.read_file(inFile)
		print('number of wards in state:', len(gdf))
		gdf = gdf.loc[gdf['CNTY_NAME'] == county]

		print('number of wards in', county, 'county:', len(gdf))

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
		
		outFile = pathlib.Path('./' + county + '_population.geojson')
		gdf.to_file(outFile, driver='GeoJSON')
		with open(outFile) as f:
			gjsn = geojson.load(f) 

		os.remove(outFile)
		
		if write_Excel:
			parent = inFile.parent
			outFile = parent.joinpath(''.join(['Local_Redistricting_', county,'Wards-shp.xlsx']))
			gdf.to_excel(outFile)

		return [target_ward_cutoff, id_list, ward_list, pop_list, focal_point, gdf, gjsn]

	else:
		print('ltsb 2021 data file not found')
		
		
def GetTargetWardsInBounds(gdf, target_ward_cutoff, write_Excel = False):
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
 