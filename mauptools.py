import maup 
import time

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
	
	id reset_crs:
		source = source.to_crs(epsg = common_epsg)
		target = target.to_crs(epsg = common_epsg)
    return mapping
    