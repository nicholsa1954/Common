ctv_map = {'C':'City of', 'V':'Village of', 'T':'Town of'}

import plotly.graph_objs as go

def GetChoroplethMapbox(gdf, gjsn, variable, range, colorscale, 
                        marker_line_color, marker_line_width, marker_opacity,
                        hoverinfo, show_scale):
    return go.Choroplethmapbox(geojson = gjsn,
        locations = gdf['id'],
        z = gdf[variable],
        featureidkey = 'properties.id',
        name = '',
        colorscale = colorscale, 
        zmin = range[0], zmax = range[1],
        marker_line_color = marker_line_color, 
        marker_line_width = marker_line_width, 
        marker_opacity = marker_opacity,
        hoverinfo = hoverinfo,
        showscale = show_scale, visible = True)
		
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

def GetHoverlabelMapbox(gdf, template, color):
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
    opacity=1.0,
    textfont={"color":color,"size":size},
    texttemplate = '%{text}',
    textposition='middle center')
	
	
	