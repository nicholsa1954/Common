import pathlib
from folium.features import DivIcon
    
def number_DivIcon(font_size, color, number):
    """ Create a 'numbered' icon """
    icon = DivIcon(
            icon_size=(150,36),
            icon_anchor=(14,40),
            html="""<span class="fa-stack " style="font-size: {}pt" >
                    <!-- The icon that will wrap the number -->
                    <span class="fa fa-circle-o fa-stack-2x" style="color : {:s}"></span>
                    <!-- a strong element with the custom content, in this case a number -->
                    <strong class="fa-stack-1x">{}</strong>
                </span>""".format(font_size, color, number)
        )
    return icon    