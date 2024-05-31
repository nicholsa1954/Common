vdlf_target_counties = [
    'Brown', 'Dane', 'Fond du Lac','Kenosha', 'Manitowoc', 
    'Milwaukee', 'Outagamie', 'Racine', 'Rock', 
    'Sheboygan', 'Trempealeau', 'Walworth', 'Waukesha', 'Winnebago']

vdlf_target_cities = [
    'Green Bay', 'Madison', 'Fond du Lac', 'Kenosha', 'Manitowoc',
    'Milwaukee', 'Appleton', 'Racine', 'Beloit',
    'Sheboygan', 'Arcadia', 'Delevan', 'Waukesha', 'Oshkosh']

vdlf_target_fips = ['55009', '55025', '55039', '55059', '55073', 
                    '55079', '55087', '55101', '55105', 
                    '55117', '55121', '55127', '55133', '55139']

county_fips_dict = dict(zip(vdlf_target_counties, vdlf_target_fips))
county_city_dict = dict(zip(vdlf_target_counties, vdlf_target_cities))

brown_county_data = dict(\
    'target_county' : 'Brown',
    'target_city' : 'Green Bay',
    'target_county_fips' : '55009',
    'target_county_fp' : '009',
    'target_city_fips' : '5500931000',
    'target_county_caps' : 'BROWN COUNTY',
    'target_city_caps' = 'City of GREEN BAY')

dane_county_data = dict(\
    'target_county' : 'Dane',
    'target_city' : 'Madison',
    'target_county_fips' : '55025',
    'target_county_fp' : '025',
    'target_city_fips' : '5502531000',
    'target_county_caps' : 'DANE COUNTY',
    'target_city_caps' = 'City of MADISON')

kenosha_county_data = dict(\    
    'target_county' : 'Kenosha',
    'target_city' : 'Kenosha',
    'target_county_fips' : '55059',
    'target_county_fp' : '059',
    'target_city_fips' : '5505931000',
    'target_county_caps' : 'KENOSHA COUNTY',
    'target_city_caps' = 'City of KENOSHA')

milwaukee_county_data = dict(\
    'target_county' : 'Milwaukee',
    'target_city' : 'Milwaukee',
    'target_county_fips' : '55079',
    'target_county_fp' : '079',
    'target_city_fips' : '5507931000',
    'target_county_caps' : 'MILWAUKEE COUNTY',
    'target_city_caps' = 'City of MILWAUKEE')

outagamie_county_data = dict(\
    'target_county' : 'Outagamie',
    'target_city' : 'Appleton',
    'target_county_fips' : '55087',
    'target_county_fp' : '087',
    'target_city_fips' : '5508731000',
    'target_county_caps' : 'OUTAGAMIE COUNTY',
    'target_city_caps' = 'City of APPLETON')

racine_county_data = dict(\
    'target_county' : 'Racine',
    'target_city' : 'Racine',
    'target_county_fips' : '55101',
    'target_county_fp' : '101',
    'target_city_fips' : '5510131000',
    'target_county_caps' : 'RACINE COUNTY',
    'target_city_caps' = 'City of RACINE')

waukesha_county_data = dict(\
    'target_county' : 'Waukesha',
    'target_city' : 'Waukesha',
    'target_county_fips' : '55133',
    'target_county_fp' : '133',
    'target_city_fips' : '5513331000',
    'target_county_caps' : 'WAUKESHA COUNTY',
    'target_city_caps' = 'City of WAUKESHA')

winnebago_county_data = dict(\
    'target_county' : 'Winnebago',
    'target_city' : 'Oshkosh',
    'target_county_fips' : '55139',
    'target_county_fp' : '139',
    'target_city_fips' : '5513931000',
    'target_county_caps' : 'WINNEBAGO COUNTY',  
    'target_city_caps' = 'City of OSHKOSH')


    