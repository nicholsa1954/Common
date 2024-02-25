import pathlib
import random
import time
from pathlib import Path
from typing import IO

import geojson
import geopandas as gpd
import pandas as pd
import shapely

from testVPNConnection import testVPNConnection

common_cols = ["id", "lat", "lon", "geometry", "z_layer"]

county_cols = ["GEOID", "CNTY_FIPS", "CNTY_NAME", *common_cols]

city_cols = ["OBJECTID", "MCD_FIPS", "MCD_NAME", "CTV", *common_cols]


def ConvertGDFtoGJSN(gdf):
    """_summary_
    This random string is a workaround to fix a problem with
    processes hanging on to a file handle after it has been closed.
    """
    randstr = str(random.randint(0, 1000))
    out_file = pathlib.Path(f"./static/{randstr}.geojson")
    gdf.to_file(out_file, driver="GeoJSON")
    with out_file.open() as f:
        gjsn = geojson.load(f)
    out_file.unlink()
    return gjsn


def InitializeGeoDataFrames(path, data_file, remote_file=True, kwargs={}):
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
        print("Returning empty DataFrame.")
    if not Path(path).exists():
        print("Can't find the path:", path, "...")
        print("Returning empty GeoDataFrame.")
        return gpd.GeoDataFrame()
    in_file = Path(path + data_file)
    if not in_file.is_file():
        print("Cant find the file:", in_file, "-- returning empty DataFrame.")
        print("Do you need to enter network credentials?")
        return gpd.GeoDataFrame()
    print("Loading data from file...")

    sfx = pathlib.Path(data_file).suffix
    start_time = time.time()
    if sfx == ".shp":
        gdf = gpd.read_file(in_file, typ="series", orient="records", **kwargs)
    else:
        print("unknown file type:", sfx)
        return gpd.GeoDataFrame()
    elapsed_time = time.time() - start_time
    print(
        "Geodata loaded, elapsed time:",
        time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),
    )
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
    gdf = gdf.to_crs("epsg:3035")
    gdf["Center_point"] = gdf["geometry"].centroid.to_crs("epsg:4326")
    gdf = gdf.to_crs("epsg:4326")

    # We want to figure the center point of the geometry so we can focus the visualization there
    focal_point = [gdf["Center_point"].y.mean(), gdf["Center_point"].x.mean()]

    # We want the center point of each polygon
    idx = list(gdf.columns).index("geometry")
    try:
        gdf.insert(idx, "lat", gdf.Center_point.map(lambda p: p.y), True)
        gdf.insert(idx + 1, "lon", gdf.Center_point.map(lambda p: p.x), True)
    except shapely.errors.GEOSException:
        gdf.insert(idx, "lat", 0.0)
        gdf.insert(idx + 1, "lon", 0.0)

    # Don't need it any more
    gdf.drop("Center_point", axis=1, inplace=True)

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
    df = df.to_crs("epsg:6933")
    areaInKMSq = df["geometry"].area / 10**6
    return float(areaInKMSq.iloc[0])


def GetCountyBounds(county_bounds_file: IO, county_name=None, write_files=False):
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
        if county_name is not None:
            gdf = gdf[gdf["COUNTY_NAM"] == county_name]
        focal_point, gdf = ComputeRegionCentroids(gdf)
        gdf["id"] = gdf["COUNTY_NAM"]
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf)

        if write_files:
            out_file = pathlib.Path(f"./static/{county_name}_bounds.geojson")
            if not out_file.exists():
                gdf.to_file(out_file, driver="GeoJSON")

            out_file = pathlib.Path(f"./static/{county_name}_bounds.shp")
            if not out_file.exists():
                gdf.to_file(out_file, driver="ESRI Shapefile")

        return [gdf, gjsn, focal_point]
    else:
        print(" ".join(["County boundary file", county_bounds_file, "not found!"]))


def GetBoundedGeometry(gdf, bounds, compute_focal_point=True):
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
    bounds_area = ComputeAreaInKMSq(bounds)

    ### ignore slivers of districts where the area of the sliver is less than .1%
    ### of the area of the boundary
    area_cutoff = bounds_area * 0.001

    # TODO: think about this, it's very expensive on a big gdf
    if gdf.crs is None:
        gdf.crs = "epsg:4326"

    gdf.to_crs("epsg:4326", inplace=True)

    # Overlay the geometry only, you don't want other data from the bounds
    # merged into your target gdf
    gdf = gpd.overlay(gdf, bounds[["geometry"]], how="intersection")
    temp = gdf.copy(deep=True)
    temp.to_crs("epsg:6933", inplace=True)
    gdf["areaKMSq"] = temp["geometry"].area / 10**6
    gdf = gdf[gdf["areaKMSq"].gt(area_cutoff)]
    focal_point = []
    if compute_focal_point:
        [focal_point, gdf] = ComputeRegionCentroids(gdf)

    if "DISTRICT" in list(gdf.columns):
        gdf["DISTRICT"] = gdf["DISTRICT"].map(lambda x: x.lstrip("0"))
        gdf = gdf[["DISTRICT", "lat", "lon", "geometry"]]
	
    return [focal_point, gdf]


def GetCountyBoardDistrictsInBounds(county_bounds_file: IO, bounds_gdf=None):
    """
    This function retrieves county board districts within a specified bounding box.

    Parameters:
    - county_bounds_file (IO): The file object representing the county bounds file.
    - bounds_gdf (GeoDataFrame): The GeoDataFrame representing the bounding box.

    Returns:
    - list: A list containing two items:
            - gdf (GeoDataFrame): The GeoDataFrame of county board districts within the bounding box.
            - gjsn (GeoJSON): The GeoJSON representation of the county board districts.

    Notes:
    - The function first checks if the county bounds file exists.
    - If the file exists, it reads the county bounds file, filters it using the bounding box, and renames the 'SUPER' column as 'DISTRICT'.
    - It then computes the centroids of the regions and resets the index of the GeoDataFrame.
    - Finally, it converts the GeoDataFrame to GeoJSON using the ConvertGDFtoGJSN function and returns both the GeoDataFrame and GeoJSON.
    - If the county bounds file does not exist, it prints an error message.
    """
    if county_bounds_file.exists():
        if bounds_gdf is not None:
            gdf = gpd.read_file(county_bounds_file, bbox=bounds_gdf)
        else:
            gdf = gpd.read_file(county_bounds_file)
        _, gdf = ComputeRegionCentroids(gdf)
        gdf = gdf.rename(columns={"SUPERID": "id"})
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[county_cols])
        return [gdf, gjsn]
    else:
        print(
            " ".join(["County board district file", county_bounds_file, "not found!"])
        )


def GetCountyBoardDistrictsInCounty(county_bounds_file: IO, county_name: str):
    """
    Get the county board districts in a specific county.

    Parameters:
    - county_bounds_file: A file object representing the county bounds file.
    - county_name: A string representing the name of the county.

    Returns:
    - A list containing two elements:
            - gdf: A GeoDataFrame object representing the county board districts.
            - gjsn: A GeoJSON object representing the county board districts.

    If the county bounds file exists, the function reads the file and filters the data to include only
    the county with the specified name. It then renames a column and computes the centroids of the regions.
    Next, it saves the GeoDataFrame to a GeoJSON file and loads the GeoJSON data into a variable.
    Finally, it removes the GeoJSON file and returns the GeoDataFrame and GeoJSON objects as a list.

    If the county bounds file does not exist, the function prints an error message.
    """
    if county_bounds_file.exists():
        gdf = gpd.read_file(county_bounds_file)
        gdf = gdf.loc[gdf["COUNTY_NAM"] == county_name]
        gdf = gdf.rename(columns={"SUPERID": "DISTRICT"})
        _, gdf = ComputeRegionCentroids(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[common_cols])
        return [gdf, gjsn]
    else:
        print(
            " ".join(["County board district file", county_bounds_file, "not found!"])
        )


def GetCountyBoardDistrictByNumber(
    county_bounds_file: IO, county_name: str, district_number: int
):
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
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[common_cols])
        return [gdf, gjsn]
    else:
        print(
            " ".join(
                ["County board district file", str(county_bounds_file), "not found!"]
            )
        )


def GetAssemblyDistrictsInCounty(
    assembly_districts_file: IO, county_bounds_file: IO, county_name: str
):
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

    If the files assembly_districts_file and county_bounds_file do not exist,
    the function prints a message indicating that the assembly district file was not found.
    """
    if assembly_districts_file.exists() and county_bounds_file.exists():
        [countyBounds, _, _] = GetCountyBounds(county_bounds_file, county_name)
        gdf = gpd.read_file(assembly_districts_file, bbox=countyBounds)
        _, gdf = ComputeRegionCentroids(gdf)
        gdf = gdf.rename(columns={"ASM2021": "id"})
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf)
        return [gdf, gjsn]
    else:
        print(
            " ".join(["Assembly district file", assembly_districts_file, "not found!"])
        )


def GetAssemblyDistrictsInBounds(assembly_districts_file: IO, bounds_gdf=None):
    """
    Given an assembly_districts_file and bounds_gdf, this function reads the assembly_districts_file,
    filters the data based on the bounds_gdf, and returns the filtered data as a GeoDataFrame and a GeoJSON object.

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
        if bounds_gdf is not None:
            gdf = gpd.read_file(assembly_districts_file, bbox=bounds_gdf)
        else:
            gdf = gpd.read_file(assembly_districts_file)
        _, gdf = ComputeRegionCentroids(gdf)
        gdf = gdf.rename(columns={"ASM2021": "id"})
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf)
        return [gdf, gjsn]
    else:
        print(
            " ".join(["Assembly district file", assembly_districts_file, "not found!"])
        )


def GetSenateDistrictsInCounty(
    senate_districts_file: IO, county_bounds_file: IO, county_name
):
    """
    Get the Senate districts within a county.

    Parameters:
    - senate_districts_file: The file containing the Senate districts data. Must be a valid file path.
    - county_bounds_file: The file containing the county bounds data. Must be a valid file path.
    - county_name: The name of the county.

    Returns:
    - A list containing the filtered Senate district data as a GeoDataFrame and GeoJSON.

    If both the `senate_districts_file` and `county_bounds_file` exist, the function reads the county bounds data and
    filters the Senate districts data based on the county bounds. It renames the columns of the filtered data and adds additional columns.
    The filtered data is then saved as a GeoJSON file and loaded as a GeoJSON object.
    Finally, the function returns the filtered data as a GeoDataFrame and the GeoJSON object.

    If either the `senate_districts_file` or `county_bounds_file` does not exist, the function displays an error message.
    """
    if senate_districts_file.exists() and county_bounds_file.exists():
        [countyBounds, _, _] = GetCountyBounds(county_bounds_file, county_name)
        gdf = gpd.read_file(senate_districts_file, bbox=countyBounds)
        _, gdf = ComputeRegionCentroids(gdf)
        gdf = gdf.rename(columns={"SEN2021": "id"})
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf)
        return [gdf, gjsn]
    else:
        print(" ".join(["Senate district file", senate_districts_file, "not found!"]))


def GetSenateDistrictsInBounds(senate_districts_file: IO, bounds_gdf=None):
    """
    Retrieves the senate districts within the specified bounding box from the given senate districts file.

    Parameters:
            senate_districts_file (IO): The file object representing the senate districts file.
            bounds_gdf: The bounding box geometry.

    Returns:
            List: A list containing two elements:
                    - gdf: The senate districts as a GeoDataFrame.
                    - gjsn: The senate districts as a GeoJSON object.

    Raises:
            FileNotFoundError: If the senate districts file does not exist.
    """
    if senate_districts_file.exists():
        if bounds_gdf is not None:
            gdf = gpd.read_file(senate_districts_file, bbox=bounds_gdf)
        else:
            gdf = gpd.read_file(senate_districts_file)
        _, gdf = ComputeRegionCentroids(gdf)
        gdf = gdf.rename(columns={"SEN2021": "id"})
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf)
        return [gdf, gjsn]
    else:
        print(" ".join(["Senate district file", senate_districts_file, "not found!"]))


def GetAldermanicDistrictsInBounds(aldermanic_districts_file: IO, bounds_gdf):
    if aldermanic_districts_file.exists():
        print(bounds_gdf.head())
        gdf = gpd.read_file(aldermanic_districts_file, bbox=bounds_gdf)
        print(gdf.columns)
        print(gdf.head())
        gdf = gdf.rename(columns={"ALDERID20": "DISTRICT"})
        _, gdf = ComputeRegionCentroids(gdf)
        gdf = gdf.rename(columns={"DISTRICT": "id"})
        gdf["z_layer"] = 0
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[city_cols])
        return [gdf, gjsn]
    else:
        print(
            " ".join(
                [
                    "Common council district file",
                    aldermanic_districts_file,
                    "not found!",
                ]
            )
        )


def GetAldermanicDistrictsInCity(
    aldermanic_districts_file: IO,
    county_name: str,
    city_name: str,
    using_local_file=False,
):
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
        gdf = gpd.read_file(aldermanic_districts_file)
        if not using_local_file:
            gdf = gdf.loc[
                (gdf["CNTY_NAME"] == county_name) & (gdf["MCD_NAME"] == city_name)
            ]
            gdf["id"] = gdf["ALDERID20"].apply(lambda x: x[-4:].lstrip("0"))

        else:
            gdf["id"] = gdf["DISTRICT"]

        _, gdf = ComputeRegionCentroids(gdf)
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gdf = gdf[common_cols]
        gjsn = ConvertGDFtoGJSN(gdf)
        return [gdf, gjsn]
    else:
        print("Aldermanic district file", aldermanic_districts_file, "not found!")


def GetPublicSchoolDistrictsInBounds(
    school_districts_file: IO, county_bounds, county_name: str, city_name: str
):
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
        gdf = gpd.read_file(school_districts_file)
        gdf = gdf.loc[gdf.DISTRICT == city_name]

        if not gdf.empty:
            return _extracted_from_GetPublicSchoolDistrictsInBounds_23(
                gdf, county_bounds
            )
        print(
            " ".join(
                [
                    "error -- file has no city with name",
                    city_name,
                    "in county with name",
                    county_name,
                ]
            )
        )
        return None, None
    else:
        print(" ".join(["School district file", school_districts_file, "not found!"]))


# TODO Rename this here and in `GetPublicSchoolDistrictsInBounds`
def _extracted_from_GetPublicSchoolDistrictsInBounds_23(gdf, county_bounds):
    _, gdf = GetBoundedGeometry(gdf, county_bounds)
    gdf = gdf.rename(columns={"DISTRICT": "id"})
    gdf["z_layer"] = [0] * len(gdf)
    gdf["temp"] = gdf["z_layer"]
    gdf.reset_index(inplace=True)
    gjsn = ConvertGDFtoGJSN(gdf)
    return [gdf, gjsn]


def GetAldermanicDistrictByNumber(
    aldermanic_districts_file: IO,
    county_bounds_file: IO,
    county_name: str,
    city_name: str,
    district_number: int,
):
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
    :return: A list containing two elements - a GeoDataFrame object containing the aldermanic district information
    for the specified district number, and a GeoJSON object representing the same information.
    :rtype: list
    """
    if aldermanic_districts_file.exists() and county_bounds_file.exists():
        [gdf, _] = GetAldermanicDistrictsInCity(
            aldermanic_districts_file, county_bounds_file, county_name, city_name
        )
        gdf = gdf.loc[gdf.DISTRICT == str(district_number)]
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf)
        return [gdf, gjsn]
    else:
        print(
            " ".join(
                ["Aldermanic district file", aldermanic_districts_file, "not found!"]
            )
        )


def GetWardsInState(ward_bounds_file: IO):
    """
    Gets the wards in a state based on the provided ward boundaries file.

    Parameters:
    - ward_bounds_file (IO): The file containing the ward boundaries.

    Returns:
    - list: A list containing two elements:
            - gdf (GeoDataFrame): The GeoDataFrame with the ward boundaries.
            - gjsn (GJSN): The GJSN representation of the ward boundaries.

    Raises:
    - FileNotFoundError: If the ward boundaries file does not exist.
    """
    if ward_bounds_file.exists():
        gdf = gpd.read_file(ward_bounds_file)
        _, gdf = ComputeRegionCentroids(gdf)
        # gdf['STR_WARDS'] = gdf['STR_WARDS'].apply(lambda x : x.lstrip('0'))
        gdf["id"] = gdf["LABEL"]
        gdf["z_layer"] = [0] * len(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[common_cols])
        return [gdf, gjsn]
    else:
        print(" ".join(["Ward boundary file", ward_bounds_file, "not found!"]))


def GetWardsInCounty(ward_bounds_file: IO, county_name: str):
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
        gdf = gdf.loc[gdf["CNTY_NAME"] == county_name]
        _, gdf = ComputeRegionCentroids(gdf)
        gdf["STR_WARDS"] = gdf["STR_WARDS"].apply(lambda x: x.lstrip("0"))
        gdf["id"] = gdf["LABEL"]
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[common_cols])
        return [gdf, gjsn]
    else:
        print(" ".join(["Ward boundary file", ward_bounds_file, "not found!"]))


def GetWardsInCity(ward_bounds_file: IO, county_name: str, city_name: str):
    """
    GetWardsInCity is a function that takes in two parameters: ward_bounds_file of type IO and city_name of type str.
    This function reads the ward_bounds_file and filters the data based on the city_name.
    It then computes the centroids of the regions and removes leading zeros from the 'STR_WARDS' column.
    The function converts the data to the 'epsg:4326' coordinate system and saves it to a GeoJSON file.
    It then loads the GeoJSON file and removes it. Finally, the function returns a list containing two elements: gdf and gjsn.

    Parameters:
    - ward_bounds_file (IO): The file object representing the ward bounds file.
    - city_name (str): The name of the city.

    Returns:
    - list: A list containing two elements: gdf and gjsn.
    """
    if ward_bounds_file.exists():
        gdf = gpd.read_file(ward_bounds_file)
        gdf = gdf.loc[
            (gdf["CNTY_NAME"] == county_name) & (gdf["MCD_NAME"] == city_name)
        ]
        print(gdf.shape, gdf.head())
        _, gdf = ComputeRegionCentroids(gdf)
        gdf["ALDERID20"] = gdf["ALDERID20"].apply(lambda x: x.lstrip("0"))
        gdf["id"] = gdf["ALDERID20"]
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[common_cols])
        return [gdf, gjsn]
    else:
        print(" ".join(["Ward boundary file", ward_bounds_file, "not found!"]))


def GetCityWardByNumber(ward_bounds_file: IO, city_name: str, ward_number: int):
    """
    This function retrieves the city ward information based on a given ward number.

    Parameters:
    - ward_bounds_file (IO): A file object representing the ward bounds file.
    - city_name (str): The name of the city.
    - ward_number (int): The ward number to retrieve information for.

    Returns:
    - list: A list containing two elements. The first element is a GeoDataFrame object containing the ward information.
    The second element is a GeoJSON object representing the ward geometry.
    """
    if ward_bounds_file.exists():
        gdf = gpd.read_file(ward_bounds_file)
        gdf = gdf.loc[gdf["MCD_NAME"] == city_name]
        gdf["ALDERID20"] = gdf["ALDERID20"].apply(lambda x: x.lstrip("0"))
        gdf = gdf.loc[gdf["ALDERID20"] == str(ward_number)]
        gdf["id"] = gdf["STR_WARDS"]
        _, gdf = ComputeRegionCentroids(gdf)
        gdf.reset_index(inplace=True)
        gjsn = ConvertGDFtoGJSN(gdf[common_cols])
        return [gdf, gjsn]
    else:
        print(" ".join(["Ward boundary file", ward_bounds_file, "not found!"]))


def GetCityInCounty(county_ward_gdf, county_name, city_name):
    """
    Given a GeoDataFrame and a city name, this function extracts the data for the specified city from the GeoDataFrame
    and creates a new GeoDataFrame and saves it as a GeoJSON file. The function takes two parameters:
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
    gdf = county_ward_gdf.loc[
        (county_ward_gdf["CNTY_NAME"] == county_name)
        & (county_ward_gdf["MCD_NAME"] == city_name)
    ].copy(deep=True)
    gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(gdf.unary_union))
    gdf = gdf.set_crs("epsg:4326")
    gdf = gdf.to_crs("epsg:4326")
    _, gdf = ComputeRegionCentroids(gdf)
    gdf["id"] = city_name
    gdf["z_layer"] = [0] * len(gdf)
    gdf.reset_index(inplace=True)
    gjsn = ConvertGDFtoGJSN(gdf[common_cols])
    return [gdf, gjsn]


def ComputeIdForMapLabel(row):
		return " ".join([row["CTV"], row["MCD_NAME"], "Ward", row["WARDID"]])


def GetWardDataFromList(
    in_file: IO, county_list, headers, numeric, geometry, write_files=False
):
    """
    GetWardDataFromList is a function that reads ward data from a file and performs various operations on it.

    Parameters:
    - in_file: An IO object representing the file to read the ward data from.
    - county_list: A list of county names to filter the ward data by.
    - headers: A list of column names to include in the resulting DataFrame.
    - numeric: A list of column names representing numeric data to include in the resulting DataFrame.
    - geometry: A list of column names representing geometric data to include in the resulting DataFrame.

    Returns:
    - gdf: A GeoDataFrame containing the filtered and processed ward data.
    """
    if in_file.exists():
        gdf = gpd.read_file(in_file)
        print("number of wards in state:", len(gdf))
        gdf = gdf.loc[gdf["CNTY_NAME"].isin(county_list)]

        print("number of wards in listed counties:", len(gdf))

        gdf = gdf[headers + numeric + geometry]
        gdf = gdf.to_crs("epsg:4326")

        # Do a little renaming
        gdf = gdf.rename(
            columns={
                "PERSONS": "Total",
                "PERSONS18": "VAP",
                "HISPANIC": "LATINX",
                "HISPANIC18": "LATINX18",
            }
        )

        gdf = gdf.rename(
            columns={
                "WHITE18": "WhiteVAP",
                "BLACK18": "BlackVAP",
                "LATINX18": "LatinxVAP",
                "ASIAN18": "AsianVAP",
            }
        )

        gdf["GEOID"] = gdf["GEOID"].astype(str)
        gdf["WARDID"] = gdf["WARDID"].astype(str)
        gdf["WARDID"] = gdf["WARDID"].apply(lambda x: x[-4:].lstrip("0"))

        gdf["id"] = gdf.apply(lambda row: ComputeIdForMapLabel(row), axis=1)
        gdf["z_layer"] = [0] * len(gdf)

        shp_file = pathlib.Path("./static/target_counties.shp")
        if write_files and not shp_file.exists():
            gdf.to_file(shp_file, driver="ESRI Shapefile")

        return gdf
    else:
        print(" ".join(["Ward data file", in_file, "not found!"]))


def GetWardDataForCounty(
    counties_gdf,
    county_name,
    target_variable="LatinxVAP",
    vap_multiplier=2.0,
    write_files=False,
):
    """
    Retrieves ward data from a larger gdf based on the provided county name.

    Args:
            counties_gdf (GeoDataFrame): The GeoDataFrame containing data for all counties.
            county_name (str): The name of the county to retrieve ward data for.
            vap_multiplier (float, optional): The multiplier used to calculate the target ward cutoff.
                    Defaults to 2.0.
            write_files (bool, optional): Specifies whether to write the data to an Excel file.
                    Defaults to False.

    Returns:
            list: A list containing the target ward cutoff, ward IDs, population IDs, population list,
                    focal point, GeoDataFrame, and GeoJSON.
    """
    gdf = counties_gdf.loc[counties_gdf["CNTY_NAME"] == county_name]
    # print('number of wards in', county_name, 'county:', len(gdf))

    temp = gdf.sort_values(by=[target_variable], ascending=False)
    pop_list = list(temp["GEOID"][0:5])
    ward_list = list(temp["WARDID"][0:5])
    mean_vap = int(temp[target_variable].mean())
    target_ward_cutoff = vap_multiplier * mean_vap
    temp = temp.loc[temp[target_variable] >= target_ward_cutoff]

    id_list = list(temp["GEOID"])
    # print('mean VAP:', mean_vap)
    # print('target_ward_cutoff:', target_ward_cutoff)
    # print('key wards:', int_list)
    # print('key wards:', sorted(list(temp['WARDID'].astype(int)) ))
    # print(temp[['WARDID',target_variable]].head(len(temp)))

    _, gdf = ComputeRegionCentroids(gdf)
    focal_point, _ = ComputeRegionCentroids(temp)

    # Compute values for voting age population percentages
    idx = list(gdf.columns).index("AsianVAP") + 1
    gdf.insert(idx, "BlackVAPPct", gdf["BlackVAP"] / gdf["VAP"])
    gdf["BlackVAPPct"] = gdf["BlackVAPPct"].fillna(0)
    gdf["BlackVAPPct"] = gdf["BlackVAPPct"].map(lambda x: "{:.2f}".format(x))
    gdf["BlackVAPPct"] = gdf["BlackVAPPct"].astype(float)

    gdf.insert(idx + 1, "LatinxVAPPct", gdf["LatinxVAP"] / gdf["VAP"])
    gdf["LatinxVAPPct"] = gdf["LatinxVAPPct"].fillna(0)
    gdf["LatinxVAPPct"] = gdf["LatinxVAPPct"].map(lambda x: "{:.2f}".format(x))
    gdf["LatinxVAPPct"] = gdf["LatinxVAPPct"].astype(float)

    gdf.insert(idx + 2, "AsianVAPPct", gdf["AsianVAP"] / gdf["VAP"])
    gdf["AsianVAPPct"] = gdf["AsianVAPPct"].fillna(0)
    gdf["AsianVAPPct"] = gdf["AsianVAPPct"].map(lambda x: "{:.2f}".format(x))
    gdf["AsianVAPPct"] = gdf["AsianVAPPct"].astype(float)

    gdf.reset_index(inplace=True)
    cols = [
        "MCD_NAME",
        "CTV",
        "WARDID",
        *county_cols,
        "AsianVAPPct",
        "AsianVAP",
        "BlackVAPPct",
        "BlackVAP",
        "LatinxVAPPct",
        "LatinxVAP",
        "VAP",
    ]
    gjsn = ConvertGDFtoGJSN(gdf[cols])

    if write_files:
        out_file = pathlib.Path("./static/" + county_name + "_population.geojson")
        if not out_file.exists():
            gdf.to_file(out_file, driver="GeoJSON")

        out_file = pathlib.Path("./static/" + county_name + "_population.shp")
        if not out_file.exists():
            gdf.to_file(out_file, driver="ESRI Shapefile")

        out_file = pathlib.Path("./static/" + county_name + "_population_data.xlsx")
        if not out_file.exists():
            data = {
                "target_ward_cutoff": target_ward_cutoff,
                "focal_point_lat": focal_point[0],
                "focal_point_lon": focal_point[1],
            }
            df = pd.DataFrame(data, index=[0])
            df.to_excel(out_file)

        out_file = pathlib.Path("./static/" + county_name + "_population_arrays.xlsx")
        if not out_file.exists():
            # df = pd.DataFrame({'id_list': id_list})
            data = {"ward_list": ward_list, "pop_list": pop_list}
            df = pd.DataFrame.from_dict(data)
            # df3 = pd.DataFrame({'pop_list': pop_list})
            # df = pd.concat([df, df2, df3], axis = 1, ignore_index = True)
            df.to_excel(out_file)

    return [target_ward_cutoff, id_list, ward_list, pop_list, focal_point, gdf, gjsn]


def GetTargetWardsInCounty(
    gdf, target_ward_cutoff, target_variable="LatinxVAP", write_files=False
):
    """
    Retrieves the target wards within the specified bounds from the given GeoDataFrame.

    Args:
            gdf (GeoDataFrame): The input GeoDataFrame.
            target_ward_cutoff (float): The threshold value for the LatinxVAP column.
            write_files (bool, optional): Flag indicating whether to write the result to an Excel file. Defaults to False.

    Returns:
            list: A list containing two elements:
                    - gdf (GeoDataFrame): The filtered GeoDataFrame.
                    - gjsn (GeoJSON): The GeoJSON representation of the filtered GeoDataFrame.
    """
    county_name = gdf.iloc[0].CNTY_NAME
    gdf = gdf.loc[gdf[target_variable] >= target_ward_cutoff]
    gdf.reset_index(inplace=True)
    gjsn = ConvertGDFtoGJSN(gdf)

    if write_files:
        out_file = pathlib.Path("./static/" + county_name + "_targetwards.geojson")
        if not out_file.exists():
            gdf.to_file(out_file, driver="GeoJSON")

        out_file = pathlib.Path("./static/" + county_name + "_targetwards.shp")
        if not out_file.exists():
            gdf.to_file(out_file, driver="ESRI Shapefile")

        out_file = pathlib.Path("./static/" + county_name + "_targetwards.xlsx")
        if not out_file.exists():
            gdf.to_excel(out_file)

    return [gdf, gjsn]


def GetPassiveWardsInCounty(
    gdf, target_ward_cutoff, target_variable="LatinxVAP", write_files=False
):
    """
    Get the passive wards in bounds.

    Parameters:
    - gdf: The GeoDataFrame containing the data.
    - target_ward_cutoff: The cutoff value for LatinxVAP.
    - write_files: Optional parameter indicating whether to write the data to an Excel file. Default is False.

    Returns:
    - A list containing the GeoDataFrame and the geojson representation of the data.
    """
    county_name = gdf.iloc[0].CNTY_NAME
    gdf = gdf.loc[gdf[target_variable] < target_ward_cutoff]
    gdf.reset_index(inplace=True)
    gjsn = ConvertGDFtoGJSN(gdf)

    if write_files:
        out_file = pathlib.Path("./static/" + county_name + "_passivewards.geojson")
        if not out_file.exists():
            gdf.to_file(out_file, driver="GeoJSON")

        out_file = pathlib.Path("./static/" + county_name + "_passivewards.shp")
        if not out_file.exists():
            gdf.to_file(out_file, driver="ESRI Shapefile")

        out_file = pathlib.Path("./static/" + county_name + "_passivewards.xlsx")
        if not out_file.exists():
            gdf.to_excel(out_file)

    return [gdf, gjsn]


def TrimGDFToBounds(gdf, bounds, bounds_area=None):
    """
    Trims a GeoDataFrame (gdf) to the provided bounds and computes the area of
    each polygon in the trimmed gdf.

    Args:
            gdf (GeoDataFrame): The input GeoDataFrame to be trimmed.
            bounds (GeoDataFrame): The bounds to trim the gdf to.

    Returns:
            list: A list containing the trimmed gdf and the computed area of
            each polygon in GeoJSON format.
    """
    if bounds_area is None:
        bounds_area = ComputeAreaInKMSq(bounds)
    area_cutoff = bounds_area * 0.001
    gdf = gpd.overlay(gdf, bounds[["geometry"]], how="intersection")
    temp = gdf.copy(deep=True)
    temp = temp.to_crs("epsg:6933")
    gdf["areaKMSq"] = temp["geometry"].area / 10**6
    gdf = gdf[gdf["areaKMSq"].gt(area_cutoff)]
    gdf.reset_index(inplace=True)
    gjsn = ConvertGDFtoGJSN(gdf[common_cols])
    return [gdf, gjsn]

    ############################
    ##### functions to support asynchronous processing




def GetDistrictsInBounds(datafile, rename_column, bounds_gdf=None):
    """
    Reads a datafile containing district information and returns the districts within specified bounds.

    Args:
        datafile (str): Path to the datafile.
        rename_column (str): Name of the column to be renamed as 'id'.
        bounds_gdf (GeoDataFrame, optional): Bounds to filter the districts. Defaults to None.

    Returns:
        GeoDataFrame: Districts within the specified bounds.
    """
    if datafile.exists():
        if bounds_gdf is not None:
            gdf = gpd.read_file(datafile, bbox=bounds_gdf)
        else:
            gdf = gpd.read_file(datafile)
        gdf = gdf.rename(columns={rename_column: "id"})
        gdf["z_layer"] = [0] * len(gdf)
        focal_point, gdf = ComputeRegionCentroids(gdf)
        return TrimGDFToBounds(gdf[common_cols], bounds_gdf)
    else:
        print(" ".join(["Data file", datafile, "not found!"]))
