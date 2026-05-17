from io import BytesIO
from pathlib import Path
import uuid
from PIL import Image as PilImage
from markupsafe import Markup


def inline_image(name: str, milimiters_w: int, milimiters_h: int, mime_type: str, suffix: str) -> str:
    xml = f"""<draw:frame draw:style-name="fr2" draw:name="{name}"
                    text:anchor-type="as-char" svg:width="{milimiters_w/10}cm"
                    svg:height="{milimiters_h/10}cm">
                    <draw:image
                        xlink:href="Pictures/{name}{suffix}"
                        xlink:type="simple" xlink:show="embed"
                        xlink:actuate="onLoad" draw:mime-type="{mime_type}" />
                </draw:frame>"""
    xml = xml.replace("\n", "")
    return xml
