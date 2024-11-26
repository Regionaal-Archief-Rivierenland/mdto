import pytest
import lxml.etree as ET
from mdto import Informatieobject, Bestand, from_file


def serialization_chain(xmlfile: str) -> str:
    """
    Implements a serialization chain by calling from_file(), and then re-converting that to XML with
    to_xml().

    Args:
        xmlfile: the xmlfile to run the chain on

    Returns:
        str: the re-serailized XML, as a string
    """
    # Deserialize
    object = from_file(xmlfile)

    # Serialize back to XML
    output_tree = object.to_xml()

    # MDTO uses tabs instead of spaces
    ET.indent(output_tree, space="\t")

    return (
        ET.tostring(
            output_tree.getroot(),
            doctype='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        ).decode("UTF-8")
        + "\n"  # MDTO closes with a newline
    )


def test_from_file_archiefstuk(voorbeeld_archiefstuk_xml):
    """Test that from_file() correctly parses Voorbeeld Archiefstuk Informatieobject.xml"""
    archiefstuk = from_file(voorbeeld_archiefstuk_xml)

    assert isinstance(archiefstuk, Informatieobject)
    assert archiefstuk.naam == "Verlenen kapvergunning Hooigracht 21 Den Haag"


def test_from_file_dossier(voorbeeld_dossier_xml):
    """Test that from_file() correctly parses Voorbeeld Dossier Informatieobject.xml"""
    dossier = from_file(voorbeeld_dossier_xml)

    assert isinstance(dossier, Informatieobject)
    assert dossier.trefwoord[1] == "kappen"


def test_from_file_serie(voorbeeld_serie_xml):
    """Test that from_file() correctly parses Voorbeeld Serie Informatieobject.xml"""
    serie = from_file(voorbeeld_serie_xml)

    assert isinstance(serie, Informatieobject)
    assert serie.naam == "Vergunningen van de gemeente 's-Gravenhage vanaf 1980"


def test_from_file_bestand(voorbeeld_bestand_xml):
    """Test that from_file() correctly parses Voorbeeld Bestand.xml"""
    bestand = from_file(voorbeeld_bestand_xml)

    assert isinstance(bestand, Bestand)
    assert (
        bestand.isRepresentatieVan.verwijzingNaam
        == "Verlenen kapvergunning Hooigracht 21 Den Haag"
    )


def test_automatic_bestand_generation(voorbeeld_bestand_xml):
    """Test if automatic Bestand XML generation matches Voorbeeld Bestand.xml"""
    # TODO: this needs to read the resource at
    # <URLBestand>https://kia.pleio.nl/file/download/55815288/0090101KapvergunningHoogracht.pdf</URLBestand>
    # but that link is dead (as all other links)
    pass


def test_serialization_chain_informatieobject(voorbeeld_archiefstuk_xml):
    """Test the serialization chain for Informatieobject"""
    output_xml = serialization_chain(voorbeeld_archiefstuk_xml)

    # Read the original file into a string
    with open(voorbeeld_archiefstuk_xml, "r", encoding="utf-8") as f:
        original_xml = f.read()

    # Ensure the serialized XML matches the original
    assert output_xml == original_xml


def test_serialization_chain_bestand(voorbeeld_bestand_xml):
    """Test the serialization chain for Bestand"""
    output_xml = serialization_chain(voorbeeld_bestand_xml)

    # Read the original file into a string
    with open(voorbeeld_bestand_xml, "r", encoding="utf-8") as f:
        original_xml = f.read()

    # Ensure the serialized XML matches the original
    assert output_xml == original_xml
