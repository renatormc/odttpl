from pathlib import Path

from lxml.etree import _ElementTree

from odttpl.odt_pos_process.archive import unpack, repack
from odttpl.odt_pos_process.parser import process_content


def pos_process_odt(input_path: str | Path, output_path: str | Path) -> None:
    input_path, output_path = str(input_path), str(output_path)
    temp_dir: str
    tree: _ElementTree
    temp_dir, tree = unpack(input_path)
    try:
        process_content(tree)
        tree.write(
            f"{temp_dir}/content.xml",
            xml_declaration=True,
            encoding="UTF-8",
        )
        repack(temp_dir, output_path)
    except Exception:
        import shutil
        shutil.rmtree(temp_dir)
        raise