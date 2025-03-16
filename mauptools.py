import maup 
import pandas as pd
import geopandas as gpd
import time
import sys
sys.path.append('./')
from gdftools import InitializeGeoDataFrames
from edatools import  ColumnMove

sys.path.append('../SEIU/SEIU_2025_Election')
from common import racine_fips_dict, brown_fips_dict, milwaukee_fips_dict

wisconsin_transverse_mercator = 3070
common_epsg = 4326

def MaupRepair(gdf):
	"""
	Repairs a GeoDataFrame if necessary using the `maup` library.
	This function checks the validity of the input GeoDataFrame using `maup.doctor`.
	If the GeoDataFrame is found to be invalid, it attempts to repair it using
	`maup.smart_repair`. The function then rechecks the validity of the repaired
	GeoDataFrame and provides feedback on whether the repair was successful.
	Args:
		gdf (geopandas.GeoDataFrame): The GeoDataFrame to be checked and potentially repaired.
	Returns:
		geopandas.GeoDataFrame: The repaired GeoDataFrame if repairs were needed, or the
		original GeoDataFrame if no repairs were necessary.
	Raises:
		ValueError: If the repair process fails and the GeoDataFrame remains invalid.
	Notes:
		- The function prints progress and status messages to the console.
		- The time taken for the repair process is also displayed.
	Example:
		>>> repaired_gdf = MaupRepair(gdf)
	"""
	start_time = time.time()
	print('Checking geodataframe...')
	
	if not maup.doctor(gdf):
		print('Repairing geodataframe ...')
		gdf = maup.smart_repair(gdf)
		if maup.doctor(gdf):
			print('Geodataframe successfully repaired.')
		else:
			print('Repair unsuccessful. Please check the data.')
	else:
		print('Geodataframe does not need repair.')
	
	elapsed_time = time.time() - start_time
	print(f'Repair process completed in {elapsed_time:.2f} seconds.')
	return gdf

def AssignGeoSourceToTarget(source, target, do_repairs = True, reset_crs = True):
	def AssignGeoSourceToTarget(source, target, do_repairs=True, reset_crs=True):
		"""
		Assigns geometries from a source GeoDataFrame to a target GeoDataFrame, with optional 
		coordinate reference system (CRS) resetting and geometry repairs.
		Parameters:
		-----------
		source : geopandas.GeoDataFrame
			The source GeoDataFrame containing geometries to be assigned.
		target : geopandas.GeoDataFrame
			The target GeoDataFrame to which geometries will be assigned.
		do_repairs : bool, optional
			If True, attempts to repair invalid geometries in both the source and target 
			GeoDataFrames before assignment. Default is True.
		reset_crs : bool, optional
			If True, resets the CRS of both the source and target GeoDataFrames to the 
			Wisconsin Transverse Mercator projection before assignment, and back to a 
			common EPSG after assignment. Default is True.
		Returns:
		--------
		mapping : pandas.Series
			A mapping of source geometries to target geometries, where the index corresponds 
			to the source geometries and the values correspond to the target geometries.
		Notes:
		------
		- The function uses the `maup.assign` method to perform the assignment.
		- The `MaupRepair` function is assumed to handle geometry repairs.
		- The CRS values `wisconsin_transverse_mercator` and `common_epsg` must be defined 
		  elsewhere in the code.
		"""

	if reset_crs:
		source = source.to_crs(epsg = wisconsin_transverse_mercator)
		target = target.to_crs(epsg = wisconsin_transverse_mercator)
		
	if do_repairs:
		print('beginning repairs...')
		print('checking source...')
		source = MaupRepair(source)
		print('checking target...')
		target = MaupRepair(target)

	mapping = maup.assign(source, target)
	
	if reset_crs:
		source = source.to_crs(epsg = common_epsg)
		target = target.to_crs(epsg = common_epsg)
	return mapping

def GetBlocksOrWards(path, file, columns_to_keep, target_county_fips):
	"""
	Processes geographic data to extract and filter blocks or wards (depending on the
 	input file) for specific counties.
  
	Args:
		path (str): The file path to the directory containing the geographic data file.
		file (str): The name of the geographic data file to be processed.
		columns_to_keep (list): A list of column names to retain in the resulting DataFrame.
		target_county_fips (list): A list of county FIPS codes to filter the data for specific counties.
	Returns:
		pandas.DataFrame: A DataFrame containing the filtered and processed geographic data 
		for the specified counties and columns.
	Notes:
		- The function initializes a GeoDataFrame from the specified file and path.
		- Filters the data based on the provided county FIPS codes 
		- Resets the index of the resulting DataFrame and applies a repair function 
		  (`MaupRepair`) to the data.
	"""
	blocks_df = InitializeGeoDataFrames(path, file, epsg=wisconsin_transverse_mercator, remote_file=False)

	print(f'Blocks/wards in state: {len(blocks_df)}')
	target_county_blocks_df = blocks_df.loc[
		blocks_df['CNTY_FIPS'].isin(target_county_fips), columns_to_keep
	]

	target_county_blocks_df = MaupRepair(target_county_blocks_df)
	target_county_blocks_df.reset_index(drop=True, inplace=True)
	return target_county_blocks_df

def MapBlocksToWards(blocks_df, wards_df, fips_dict, variables, target_mcd_name = None):
    """
    Processes county wards by assigning blocks to wards and aggregating variables.

    Parameters:
        blocks_df (GeoDataFrame): GeoDataFrame containing block-level data.
        wards_df (GeoDataFrame): GeoDataFrame containing ward-level data.
        fips_dict (dict): Dictionary mapping MCD names to FIPS codes.
        variables (list): List of variables (columns) to aggregate.

    Returns:
        GeoDataFrame: Processed county wards with aggregated variables.
    """
    county_wards = gpd.GeoDataFrame()

    for mcd_name, mcd_fips in fips_dict.items():
        if target_mcd_name is not None and mcd_name != target_mcd_name:
            continue
        print(mcd_name, mcd_fips)

        blocks = blocks_df.query("MCD_FIPS == @mcd_fips").reset_index(drop=True)
        wards = wards_df.query("MCD_FIPS == @mcd_fips").reset_index(drop=True)

        print(f'blocks in {mcd_name}:', len(blocks), f'-- wards in {mcd_name}:', len(wards))

        block_to_ward_assignment = maup.assign(blocks, wards).fillna(0).astype(int)
        print(len(block_to_ward_assignment), block_to_ward_assignment.min(), block_to_ward_assignment.max())

        wards[variables] = (
            blocks[variables]
            .groupby(block_to_ward_assignment)
            .sum(numeric_only=True)
            .fillna(0)
            .astype(int)
        )

        county_wards = pd.concat([county_wards, wards], ignore_index=True)

    ndx = county_wards.columns.get_loc('geometry')
    county_wards = ColumnMove(county_wards, 'geometry', ndx)
    county_wards.reset_index(inplace=True, drop=True)

    return county_wards



    