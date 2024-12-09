import maup 

wisconsin_transverse_mercator = 3070
common_epsg = 4326

def AssignGeoSourceToTarget(source, target):
    source = source.to_crs(epsg = wisconsin_transverse_mercator)
    target = target.to_crs(epsg = wisconsin_transverse_mercator)
    
    source_needs_repair = not maup.doctor(source)
    if source_needs_repair:
        tmp = maup.smart_repair(source)
        fixed = maup.doctor(tmp)
        assert fixed == True, "Source is not fixed"
        source = tmp
        
    target_needs_repair = not maup.doctor(target)
    if target_needs_repair:
        tmp = maup.smart_repair(target)
        fixed = maup.doctor(tmp)
        assert fixed == True, "Target is not fixed"
        target = tmp
    
    mapping = maup.assign(source, target)
    source = source.to_crs(epsg = common_epsg)
    target = target.to_crs(epsg = common_epsg)
    return mapping
    