import pytest
import requests
import zipfile
from io import BytesIO
from pathlib import Path

xml_url = "https://www.nationaalarchief.nl/sites/default/files/field-file/MDTO-XML%201.0.1%20Voorbeelden%20%283%29.zip"

# list of example files in the zip file
prefix = "MDTO-XML 1.0.1 Voorbeeld "
xml_voorbeelden = [
    f"{prefix}Archiefstuk Informatieobject.xml",
    f"{prefix}Dossier Informatieobject.xml",
    f"{prefix}Serie Informatieobject.xml",
    f"{prefix}Bestand.xml",
]


def download_mdto_voorbeelden(target_dir):
    """Downloads the MDTO example files, and extracts the zip to `target_dir`"""
    response = requests.get(xml_url)
    response.raise_for_status()  # raise error if download failed

    # unpack zip file
    with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(target_dir)


@pytest.fixture
def mdto_example_files(pytestconfig, tmp_path_factory):
    """Make (cached) MDTO example files available as a fixture"""

    # retrieve path to cached MDTO XML examples
    cache_path = pytestconfig.cache.get("voorbeelden/cache_path", None)
    # check if cached files exists
    if cache_path is None or not all(
        ((cache_path := Path(cache_path)) / xml_file).exists()
        for xml_file in xml_voorbeelden
    ):
        # download MDTO XML examples to tmpdir
        cache_path = tmp_path_factory.mktemp("MDTO Voorbeeld Bestanden")
        download_mdto_voorbeelden(cache_path)
        pytestconfig.cache.set("voorbeelden/cache_path", str(cache_path))

    # create {filename : file_path} dict
    xml_file_paths = {
        xml_file.removeprefix(prefix): str(cache_path / xml_file)
        for xml_file in xml_voorbeelden
        if (cache_path / xml_file).exists()
    }

    return xml_file_paths


@pytest.fixture
def voorbeeld_archiefstuk_xml(mdto_example_files):
    return mdto_example_files["Archiefstuk Informatieobject.xml"]


@pytest.fixture
def voorbeeld_dossier_xml(mdto_example_files):
    return mdto_example_files["Dossier Informatieobject.xml"]


@pytest.fixture
def voorbeeld_serie_xml(mdto_example_files):
    return mdto_example_files["Serie Informatieobject.xml"]


@pytest.fixture
def voorbeeld_bestand_xml(mdto_example_files):
    return mdto_example_files["Bestand.xml"]
