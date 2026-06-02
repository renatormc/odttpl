import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from lxml.etree import _ElementTree


def unpack(odt_path: str) -> tuple[str, _ElementTree]:
    temp_dir = tempfile.mkdtemp(prefix="posodt_")
    with zipfile.ZipFile(odt_path, "r") as z:
        z.extractall(temp_dir)
    content_path = os.path.join(temp_dir, "content.xml")
    tree = etree.parse(content_path)
    return temp_dir, tree


def repack(temp_dir: str, output_path: str) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        mimetype_path = os.path.join(temp_dir, "mimetype")
        if os.path.exists(mimetype_path):
            z.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                if arcname == "mimetype":
                    continue
                z.write(file_path, arcname)
    shutil.rmtree(temp_dir)