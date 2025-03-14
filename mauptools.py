import maup 
import time
import sys
sys.path.append('./')
from gdftools import InitializeGeoDataFrames

sys.path.append('../SEIU/SEIU_2025_Election')
from common import racine_fips_dict, brown_fips_dict, milwaukee_fips_dict

wisconsin_transverse_mercator = 3070
common_epsg = 4326

def MaupRepair(gdf):
	start = time.time()
	print('checking geodataframe...')
	needs_repair = not maup.doctor(gdf)
	print('geodataframe needs repair:', needs_repair)
	if(needs_repair):
		print('repairing gdf...')
		fixed_gdf = maup.smart_repair(gdf)
		fixed = maup.doctor(fixed_gdf)
		print('gdf now fixed: ', fixed)
		gdf = fixed_gdf
	print('returning gdf.')  
	print('elapsed time:', start-time.time(), 'seconds')
	return gdf
	
"""
usage:  for example

    block_to_precinct_assignment = AssignSourceToTarget(mke_county_blocks_df, mke_county_precincts_df).fillna(0).astype(int)
    print('Blocks assigned to precincts: ', len(block_to_precinct_assignment[block_to_precinct_assignment != 0]))
	mke_county_blocks_df['WARDID_24'] = block_to_precinct_assignment.astype(str)
	
"""	

def AssignGeoSourceToTarget(source, target, do_repairs = True, reset_crs = True):

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

def GetBlocksOrWards(path, file, columns_to_keep, target_county_fips ):
    blocks_df = InitializeGeoDataFrames(path, file, epsg = 3070, remote_file=False)

    print('blocks in state: ', len(blocks_df))
    target_county_blocks_df = blocks_df.loc[blocks_df['CNTY_FIPS'].isin(target_county_fips)][columns_to_keep]

    target_county_blocks_df = target_county_blocks_df.loc[
        (target_county_blocks_df['MCD_FIPS'].isin(milwaukee_fips_dict.values())) |
        (target_county_blocks_df['MCD_FIPS'].isin(racine_fips_dict.values())) |
        (target_county_blocks_df['MCD_FIPS'].isin(brown_fips_dict.values()))]

    target_county_blocks_df.reset_index(drop=True, inplace=True)
    needs_repair = not maup.doctor(target_county_blocks_df)
    print('Dataframe needs repair:', needs_repair)

    if needs_repair:
        fixed_wards = maup.smart_repair(target_county_blocks_df)
        fixed = maup.doctor(fixed_wards)
        print('Dataframe is fixed: ', fixed)
        target_county_blocks_df = fixed_wards
        
    return target_county_blocks_df



    