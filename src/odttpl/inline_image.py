from io import BytesIO
from typing import TYPE_CHECKING, Any
from pathlib import Path
import uuid
from PIL import Image as PilImage
from markupsafe import Markup
if TYPE_CHECKING:
    from .odttpl import Renderer


def totag(tag: str, *args) -> str:
    args_str = ",".join(args)
    return f"@{tag}({args_str})"


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


class InlineImage:
    def __init__(self, engine: 'Renderer') -> None:
        self.engine = engine

    def __call__(self, path: Path | str, w: int | None = None, h: int | None = None, max_w: int | None = None, max_h: int | None = None) -> Any:
        path = Path(path)
        if w is None and h is None:
            raise Exception("w or h is required")
        img = PilImage.open(path)
        alfa = img.height/img.width
        if h is None and w is not None:
            h = int(alfa*w)
        if w is None and h is not None:
            w = int(h/alfa)

        assert w is not None and h is not None
        name = uuid.uuid4().hex

        if max_w is not None and w > max_w:
            w = max_w
            h = int(alfa * w)
        if max_h is not None and h > max_h:
            h = max_h
            w = int(h / alfa)

        mime_type = img.get_format_mimetype()
        assert mime_type is not None
        xml = inline_image(name, w, h, mime_type, path.suffix)
        buf = BytesIO()
        img.save(buf, format=img.format)
        buf.seek(0)

        self.engine.add_media_to_archive(buf, mime_type, name)
        return Markup(xml)
   
