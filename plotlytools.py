
import plotly.colors
import plotly.graph_objs as go
import numpy as np

ctv_map = {'C':'City of', 'V':'Village of', 'T':'Town of'}

def GetBubbleMapbox(gdf, display_variable, color_for_positive, color_for_negative ):
    lat = gdf['lat'].values
    lon = gdf['lon'].values
    a = gdf[display_variable].values
    sizes = 6.0 + (.05 * np.abs(a))
    colors = np.where(a >= 0, color_for_positive, color_for_negative)
    # symbols = np.where(a >= 0, 'arrow-left', 'arrow-right')

    # # calculate coordinates of second vector point
    # dx = lat + np.cos(np.radians(15)) * sizes
    # dy = lon + np.sin(np.radians(15)) * sizes

    # # add start and end points to array
    # xx = np.c_[lat, dx]
    # yy = np.c_[lon, dy]
    
    return go.Scattermapbox(
        lat=lat, lon=lon, 
        mode='markers', 
        showlegend=True,
        name = 'Blue/Red = Harris Net Gain/Loss',
        hoverinfo='skip',
        marker=go.scattermapbox.Marker(
            symbol='circle',
            size=sizes,
            color=colors,
            opacity=1.0,
            allowoverlap=True)
    )

def GetChoroplethMapbox(gdf, gjsn, variable, range, colorscale, 
                        marker_line_color, marker_line_width, marker_opacity,
                        hoverinfo, show_scale, visible = True):
    if len(range) == 3:
        zmin, zmid, zmax = range[0], range[1], range[2]
    elif len(range) == 2:
        zmin, zmax = range[0], range[1]
        zmid = None
    return go.Choroplethmapbox(geojson = gjsn,
        locations = gdf['id'],
        z = gdf[variable],
        featureidkey = 'properties.id',
        name = '',
        colorscale = colorscale, 
        zmin = zmin,
        zmax = zmax,
        # zmid = zmid,
        # zmid = 0,
        marker_line_color = marker_line_color, 
        marker_line_width = marker_line_width, 
        marker_opacity = marker_opacity,
        hoverinfo = hoverinfo,
        showscale = show_scale, 
        visible = visible
) 
		
def GetScatterPlot(df, x, y, mode, name, showlegend = True):
    return go.Scatter(x=df[x], y = df[y], mode = mode, name = name, text = name, showlegend = showlegend)

def GetScatterMapbox(df, size, color, name, showlegend = True):
    return go.Scattermapbox(
        lat=df.loc[:, 'lat'],
        lon=df.loc[:, 'lon'],
        showlegend = showlegend,
        name=name,
        mode = 'markers',
        marker=go.scattermapbox.Marker(
            symbol='circle',
            size=size,
            color=color,
            opacity=1.0,
            allowoverlap=True))

def GetOutlineMapbox(gdf, gjsn, colorscale, line_color, line_width):
    return go.Choroplethmapbox(geojson = gjsn, 
        locations = gdf['id'], 
        z = gdf['z_layer'], 
        name = '',
        hoverinfo = 'skip',
        featureidkey = 'properties.id',
        colorscale = colorscale,
        marker_line_color = line_color, 
        marker_line_width = line_width, 
        marker_opacity = 1.0,
        showscale = False, visible = True)

def CreateHoverTemplate(gdf):
    result = []
    for row in gdf.itertuples():
        # pct = f"""{100*row.LatinxVAPPct:.0f}%"""
        # geopandas truncates header names to 10 characters
        # this becomes a problem when we reconstruct a gdf from a geojson file
        pct = f"""{100*row.LatinxVAPP:.0f}%"""  
        row1 = ' '.join(['<b>'+ctv_map[row.CTV], row.MCD_NAME, 'Ward', row.WARDID+'</b>'])
        row2 = ' '.join(['Latinx VAP:', str(row.LatinxVAP)])
        row3 = ' '.join(['Total VAP:', str(row.VAP)])
        row4 = ' '.join(['Latinx VAP / Total VAP:', pct])
        template = '<br>'.join([row1, row2, row3, row4])
        result.append(template)
    return result

def GetHoverLabelMapbox(gdf, template, color):
    return go.Scattermapbox(
        mode = 'text',
        name = '',
        lat = gdf.loc[:, 'lat'],
        lon = gdf.loc[:, 'lon'],
        hovertemplate = template,
        hoverlabel=dict(
            bgcolor=color))

def GetStaticLabelMapbox(gdf, color, size, text_field = 'WARDID', hoverinfo = 'skip'):
    return go.Scattermapbox(
    mode='text',
    name = '',
    hoverinfo = hoverinfo,
    lat=gdf.loc[:, 'lat'],
    lon=gdf.loc[:, 'lon'],
    text = gdf.loc[:, text_field],
    hovertext = gdf.loc[:, text_field],
    opacity=1.0,
    textfont={"color":color,"size":size, "weight":"bold"},
    texttemplate = '%{text}',
    textposition='middle center')
    
def is_valid_diverging_colorscale(colorscale_name):
    try:
        # Try accessing the colorscale by its name
        if getattr(plotly.colors.diverging, colorscale_name):
            return True
    except AttributeError:
        return False

def parse_tuple(tuple):
    return f'rgba({tuple[0]},{tuple[1]},{tuple[2]},{tuple[3]})'    
	
def ComputeZeroCenteredDivergingColorscale(gdf, display_variable, sample_colorscale, alpha = .50):
    if not is_valid_diverging_colorscale(sample_colorscale):
        return sample_colorscale
    colorscale = plotly.colors.get_colorscale(sample_colorscale)
    tuple_0 = plotly.colors.unlabel_rgb(colorscale[0][1]) + (alpha,)
    tuple_1 = plotly.colors.unlabel_rgb(colorscale[-1][1]) + (alpha,)
    color_0 = plotly.colors.color_parser(tuple_0, parse_tuple)
    color_1 = plotly.colors.color_parser(tuple_1, parse_tuple)
    white = f'rgba(255, 255, 255, {alpha})'
    zero_point = np.abs((0.0 - min(gdf[display_variable])) / (max(gdf[display_variable]) - min(gdf[display_variable])))
    return[[0.0, color_0], [zero_point, white], [1.0, color_1]]
	