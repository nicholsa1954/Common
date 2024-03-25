vdlf_target_counties = [
    'Brown', 'Calumet', 'Dane', 'Fond du Lac','Kenosha', 'Manitowoc', 
    'Milwaukee', 'Outagamie', 'Racine', 'Rock', 
    'Sheboygan', 'Trempealeau', 'Walworth', 'Waukesha', 'Winnebago']

vdlf_target_cities = [
    'Green Bay', 'Appleton', 'Madison', 'Fond du Lac', 'Kenosha', 'Manitowoc',
    'Milwaukee', 'Appleton', 'Racine', 'Beloit',
    'Sheboygan', 'Arcadia', 'Delevan', 'Waukesha', 'Oshkosh']

vdlf_target_fips = ['55009', '55015', '55025', '55039', '55059', '55073', 
                    '55079', '55087', '55101', '55105', 
                    '55117', '55121', '55127', '55133', '55139']

county_fips_dict = dict(zip(vdlf_target_counties, vdlf_target_fips))
county_city_dict = dict(zip(vdlf_target_counties, vdlf_target_cities))