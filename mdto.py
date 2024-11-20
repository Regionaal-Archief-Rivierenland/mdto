import os
import shutil
import sys
import subprocess
import hashlib
from typing import TextIO, List
from datetime import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass

# Make into an optional dependency?
import validators

# globals
MAX_NAAM_LENGTH = 80
_force, _quiet = False, False

# Helper methods
def _process_file(file_or_filename) -> TextIO:
    """
    Return file-object if input is already a file.
    Otherwise, assume the argument is a path, and convert
    it to a new file-object.

    Note: the returned file-object is always in read-only mode
    """

    # filename?
    if isinstance(file_or_filename, str):
        return open(file_or_filename, "r")
    # file-like object?
    elif hasattr(file_or_filename, "read"):
        # if file-like object, force it to be opened read-only
        if file_or_filename.writable():
            filename = file_or_filename.name
            file_or_filename.close()
            return open(filename, "r")
        else:
            return file_or_filename
    else:
        raise TypeError(
            f"Expected file object or str, but got value of type {type(file_or_filename)}"
        )


def _log(m):
    if _quiet:
        return
    else:
        print(m, file=sys.stderr)


def _warn(warning):
    """Log warning, and exit if force == False"""
    orange = "\033[33m"
    esc_end = "\033[0m"

    warning = f"{orange}Warning: {warning} "
    warning += "Continuing anyway." if _force else "Exiting."
    warning += esc_end

    _log(warning)
    if not _force:
        sys.exit(-1)


def _error(error):
    """Log error and exit"""

    red = "\033[31m"
    esc_end = "\033[0m"

    _log(f"{red}Error: {error}{esc_end}")
    sys.exit(-1)


@dataclass
class IdentificatieGegevens:
    """MDTO identificatieGegevens class.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/identificatieGegevens

    Args:
        identificatieKenmerk (str): Een kenmerk waarmee een object geïdentificeerd kan worden
        identificatieBron (str): Herkomst van het kenmerk
    """

    identificatieKenmerk: str
    identificatieBron: str

    def to_xml(self, root: str) -> ET.Element:
        """Transform IdentificatieGegevens into XML tree

        Args:
            root (str): name of the new root tag

        Returns:
            ET.Element: XML representation of IdentificatieGegevens with new root tag
        """

        root = ET.Element(root)

        kenmerk = ET.SubElement(root, "identificatieKenmerk")
        kenmerk.text = self.identificatieKenmerk

        bron = ET.SubElement(root, "identificatieBron")
        bron.text = self.identificatieBron

        return root


@dataclass
class VerwijzingGegevens:
    """MDTO verwijzingGegevens class.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/verwijzingsGegevens

    Args:
        verwijzingNaam (str): Naam van het object waarnaar verwezen wordt
        verwijzingIdentificatie (IdentificatieGegevens, optional): Identificatie van het object waarnaar verwezen wordt
    """

    verwijzingNaam: str
    verwijzingIdentificatie: IdentificatieGegevens = None

    # @property
    # def verwijzingNaam(self):
    #     """Value of MDTO 'verwijzingNaam' tag.

    #     Valid values:
    #         any string of up to 80 characters in length
    #     MDTO docs:
    #         https://www.nationaalarchief.nl/archiveren/mdto/verwijzingNaam
    #     """
    #     return self._verwijzingNaam

    # @verwijzingNaam.setter
    # def verwijzingNaam(self, val):
    #     if len(val) > MAX_NAAM_LENGTH:
    #         _warn(f"value '{val}' of element 'verwijzingNaam' "
    #               f"exceeds maximum length of {MAX_NAAM_LENGTH}.")
    #     self._verwijzingNaam = val

    def to_xml(self, root: str) -> ET.Element:
        """Transform VerwijzingGegevens into XML tree.

        Args:
            root (str): name of the new root tag

        Returns:
            ET.Element: XML representation of VerwijzingGegevens with new root tag
        """

        root = ET.Element(root)

        verwijzingnaam = ET.SubElement(root, "verwijzingNaam")
        verwijzingnaam.text = self.verwijzingNaam

        if self.verwijzingIdentificatie:
            # append lxml element directly to tree,
            # and set name of the root element to 'verwijzingIdentificatie'
            root.append(self.verwijzingIdentificatie.to_xml("verwijzingIdentificatie"))

        return root


@dataclass
class BegripGegevens:
    """MDTO begripGegevens class.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/begripGegevens

    Args:
        begripLabel (str): De tekstweergave van het begrip dat is toegekend in de begrippenlijst
        begripBegrippenlijst (VerwijzingGegevens): Verwijzing naar een beschrijving van de begrippen
        begripCode (str, optional): De code die aan het begrip is toegekend in de begrippenlijst
    """

    begripLabel: str
    begripBegrippenlijst: VerwijzingGegevens
    begripCode: str = None

    def to_xml(self, root: str) -> ET.Element:
        """Transform BegripGegevens into XML tree.

        Args:
            root (str): name of the new root tag

        Returns:
            ET.Element: XML representation of BegripGegevens with new root tag
        """

        root = ET.Element(root)

        begriplabel = ET.SubElement(root, "begripLabel")
        begriplabel.text = self.begripLabel

        if self.begripCode:
            begripcode = ET.SubElement(root, "begripCode")
            begripcode.text = self.begripCode

        root.append(self.begripBegrippenlijst.to_xml("begripBegrippenlijst"))

        return root

# FIXME: allow users to specify a filepath or an file-like object
class ChecksumGegevens:
    """MDTO checksumGegevens class.

    Takes a file-like object, and then generates the requisite checksum-metadata (i.e.
    `checksumAlgoritme`, `checksumWaarde`, and `checksumDatum`) from that file.

    Note that, when building Bestand objects, it's often easier to call the convience function `create_bestand()`.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/checksum

    Example:
        ```python
        with open("data/scan-003.jpg", "r") as myfile:
            # users may manually specify the checksum algorithm to use
            checksum = ChecksumGegevens(myfile, algorithm="sha512")
        ```

    Args:
        infile (TextIO): file-like object to generate checksum data for
        algorithm (str, optional): checksum algorithm to use; defaults to sha256. For valid values, see https://docs.python.org/3/library/hashlib.html
    """

    def __init__(self, infile: TextIO, algorithm: str = "sha256"):
        """Create a new ChecksumGegevens object."""

        verwijzing = VerwijzingGegevens(
            verwijzingNaam="Begrippenlijst ChecksumAlgoritme MDTO"
        )

        self.checksumAlgoritme = BegripGegevens(
            begripLabel=algorithm.upper().replace("SHA", "SHA-"),
            begripBegrippenlijst=verwijzing,
        )

        # file_digest() expects a file in binary mode, hence `infile.buffer.raw`
        # FIXME: this value is not the same on each call?
        self.checksumWaarde = hashlib.file_digest(
            infile.buffer.raw, algorithm
        ).hexdigest()

        self.checksumDatum = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def to_xml(self) -> ET.Element:
        """Transform ChecksumGegevens into XML tree with the following structure:

         ```xml
         <checksum>
             <checksumAlgoritme>
                 …
             </checksumAlgoritme>
             <checksumWaarde>…</checksumWaarde>
             <checksumDatum>…</checksumDatum>
         </checksum>

         ```

        Returns:
             ET.Element: XML representation of object
        """

        root = ET.Element("checksum")

        root.append(self.checksumAlgoritme.to_xml("checksumAlgoritme"))

        checksumWaarde = ET.SubElement(root, "checksumWaarde")
        checksumWaarde.text = self.checksumWaarde

        checksumDatum = ET.SubElement(root, "checksumDatum")
        checksumDatum.text = self.checksumDatum

        return root


@dataclass
class BeperkingGebruikGegevens:
    """MDTO beperkingGebruik class.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/beperkingGebruik

    Args:
        beperkingGebruikType (BegripGegevens): Typering van de beperking
        beperkingGebruikNadereBeschrijving (str, optional): Beschrijving van de beperking
        beperkingGebruikDocumentatie (VerwijzingGegevens, optional): Verwijzing naar een beschrijving van de beperking
        # FIXME: should be termijnGegevens
        beperkingGebruikTermijn (str, optional): Termijn waarbinnen de beperking op het gebruik van toepassing is
    """

    beperkingGebruikType: BegripGegevens
    beperkingGebruikNadereBeschrijving: str = None
    # TODO: this can be a list
    beperkingGebruikDocumentatie: VerwijzingGegevens = None
    # TODO: maak een TermijnGegevens dataclass
    beperkingGebruikTermijn: str = None

    def to_xml(self) -> ET.Element:
        """Transform BeperkingGebruikGegevens into XML tree

        Returns:
            ET.Element: XML representation of BeperkingGebruikGegevens
        """

        root = ET.Element("beperkingGebruik")

        root.append(self.beperkingGebruikType.to_xml("beperkingGebruikType"))

        if self.beperkingGebruikNadereBeschrijving:
            nadereBeschrijving = ET.SubElement(
                root, "beperkingGebruikNadereBeschrijving"
            )
            nadereBeschrijving.text = self.beperkingGebruikNadereBeschrijving
        if self.beperkingGebruikDocumentatie:
            root.append(
                self.beperkingGebruikDocumentatie.to_xml("beperkingGebruikDocumentatie")
            )
        if self.beperkingGebruikTermijn:
            beperkingGebruikTermijn = ET.SubElement(root, "beperkingGebruikTermijn")
            beperkingGebruikTermijn.text = self.beperkingGebruikTermijn

        return root


@dataclass
class DekkingInTijdGegevens:
    """MDTO dekkingInTijd class.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/dekkingInTijd

    Args:
        dekkingInTijdType (BegripGegevens): Typering van de periode waar het informatieobject betrekking op heeft
        dekkingInTijdBegindatum (str): Begindatum van de periode waar het informatieobject betrekking op heeft
        dekkingInTijdEinddatum (str, optional): Einddatum van de periode waar het informatieobject betrekking op heeft
    """

    dekkingInTijdType: BegripGegevens
    beginDatum: str
    eindDatum: str

    def to_xml(self) -> ET.Element:
        root = ET.Element("dekkingInTijd")
        root.append(self.dekkingInTijdType.to_xml("dekkingInTijdType"))
        begin_datum_elem = ET.SubElement(root, "dekkingInTijdBegindatum")
        begin_datum_elem.text = self.beginDatum
        eind_datum_elem = ET.SubElement(root, "dekkingInTijdEinddatum")
        eind_datum_elem.text = self.eindDatum
        return root


@dataclass
class EventGegevens:
    """MDTO eventGegevens class.

    MDTO docs:
        https://www.nationaalarchief.nl/archiveren/mdto/event

    Args:
        eventType (BegripGegevens): Aanduiding van het type event
        eventTijd (str, optional): Tijdstip waarop het event heeft plaatsgevonden
        eventVerantwoordelijkeActor (VerwijzingGegevens, optional): Actor die verantwoordelijk was voor de gebeurtenis
        eventResultaat (str, optional): Beschrijving van het resultaat van het event
    """

    eventType: BegripGegevens
    eventTijd: str  # Aangepast naar str
    eventVerantwoordelijkeActor: VerwijzingGegevens
    eventResultaat: str

    def to_xml(self) -> ET.Element:
        root = ET.Element("event")

        root.append(self.eventType.to_xml("eventType"))

        event_tijd_elem = ET.SubElement(root, "eventTijd")
        event_tijd_elem.text = self.eventTijd

        root.append(
            self.eventVerantwoordelijkeActor.to_xml("eventVerantwoordelijkeActor")
        )

        event_resultaat_elem = ET.SubElement(root, "eventResultaat")
        event_resultaat_elem.text = self.eventResultaat

        return root


@dataclass
class RaadpleeglocatieGegevens:
    """MDTO raadpleeglocatie class.

    MDTO docs: https://www.nationaalarchief.nl/archiveren/mdto/raadpleeglocatie

    Args:
        raadpleeglocatieFysiek (VerwijzingGegevens, optional): Fysieke raadpleeglocatie van het informatieobject
        raadpleeglocatieOnline (str, optional): Online raadpleeglocatie van het informatieobject; moet een valide URL zijn
    """

    raadpleeglocatieFysiek: VerwijzingGegevens = None
    raadpleeglocatieOnline: str = None

    def to_xml(self):
        root = ET.Element("raadpleeglocatie")

        # In MDTO, raadpleeglocatie may have no children, strangely enough
        if self.raadpleeglocatieFysiek:
            root.append(self.raadpleeglocatieFysiek.to_xml('raadpleeglocatieFysiek'))

        if self.raadpleeglocatieOnline:
            raadpleeglocatie_online_elem = ET.SubElement(root, "raadpleeglocatieOnline")
            raadpleeglocatie_online_elem.text = self.raadpleeglocatieOnline

        return root

    @property
    def raadpleeglocatieOnline(self):
        """Value of MDTO `raadpleeglocatieOnline` tag.

        Valid value: any RFC 3986 compliant URI

        MDTO docs: https://www.nationaalarchief.nl/archiveren/mdto/raadpleeglocatieOnline
        """
        return self._raadpleeglocatieOnline

    @raadpleeglocatieOnline.setter
    def raadpleeglocatieOnline(self, url: str):
        # if url is not set, (e.g. when calling RaadpleegLocatieGegevens() without arguments)
        # it will not be None, but rather an empty "property" object
        if isinstance(url, property) or url is None: # check if empty
            self._raadpleeglocatieOnline = None
        elif validators.url(url):
            self._raadpleeglocatieOnline = url
        else:
            _warn(f"URL '{url}' is malformed.")
            self._raadpleeglocatieOnline = url


# TODO: this should be a subclass of a general object class
@dataclass
class Informatieobject:
    """MDTO Informatieobject class.

    MDTO docs: https://www.nationaalarchief.nl/archiveren/mdto/informatieobject

    Example:

    ```python
    # Maak informatieobject
    informatieobject = Informatieobject(IdentificatieGegevens(…), naam="Kapvergunning", …)

    xml = informatieobject.to_xml()
    with open("informatieobject.xml", 'w') as output_file:
        xml.write(output_file, xml_declaration=True, short_empty_elements=False)
    ```

    Args:
        identificatie (IdentificatieGegevens | List[IdentificatieGegevens]): Gegevens waarmee het object geïdentificeerd kan worden
        naam (str): Betekenisvolle aanduiding waaronder het object bekend is
        aggregatieNiveau (BegripGegevens, optional): Aggregatieniveau van het informatieobject
        classificatie (BegripGegevens, optional): Classificatie van het informatieobject
        trefwoord (str, optional): Trefwoord dat het informatieobject beschrijft
        omschrijving (str, optional): Omschrijving van het informatieobject
        dekkingInTijd (DekkingInTijdGegevens, optional): Periode waarop het informatieobject betrekking heeft
        event (EventGegevens, optional): Gebeurtenis gerelateerd aan het informatieobject
        waardering (BegripGegevens): Waardering van het informatieobject volgens een selectielijst
        bevatOnderdeel (VerwijzingGegevens, optional): Verwijzing naar een ander onderdeel dat deel uitmaakt van het informatieobject.
        aanvullendeMetagegevens (VerwijzingGegevens, optional): Verwijzing naar een bestand dat aanvullende (domeinspecifieke) metagegevens over het informatieobject bevat
        archiefvormer (VerwijzingGegevens | List[VerwijzingGegevens]): Organisatie die verantwoordelijk is voor het opmaken en/of ontvangen van het informatieobject
        beperkingGebruik (BeperkingGebruikGegevens | List[BeperkingGebruikGegevens]): Beperking die gesteld is aan het gebruik van het informatieobject

    """

    naam: str
    identificatie: IdentificatieGegevens | List[IdentificatieGegevens]
    archiefvormer: VerwijzingGegevens | List[VerwijzingGegevens]
    beperkingGebruik: BeperkingGebruikGegevens | List[BeperkingGebruikGegevens]
    waardering: BegripGegevens
    aggregatieNiveau: BegripGegevens = None
    classificatie: BegripGegevens = None
    trefwoord: str = None
    omschrijving: str = None
    dekkingInTijd: DekkingInTijdGegevens = None
    event: EventGegevens = None
    bevatOnderdeel: VerwijzingGegevens | List[VerwijzingGegevens] = None
    aanvullendeMetagegevens: VerwijzingGegevens | List[VerwijzingGegevens] = None
    isOnderdeelVan: VerwijzingGegevens = None
    # TODO: add other elements

    def to_xml(self) -> ET.ElementTree:
        """
        Transform Informatieobject into an XML tree with the following structure:

        ```xml
        <MDTO xmlns=…>
            <informatieobject>
                …
            </informatieobject>
        </MDTO>
        ```

        Returns:
            ET.ElementTree: XML tree representing the Informatieobject object.
        """

        mdto = ET.Element(
            "MDTO",
            attrib={
                "xmlns": "https://www.nationaalarchief.nl/mdto",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd",
            },
        )

        root = ET.SubElement(mdto, "informatieobject")

        # allow users to pass either a single IdentificatieGegevens object, or a list thereof
        if isinstance(self.identificatie, IdentificatieGegevens):
            self.identificatie = [self.identificatie]

        for i in self.identificatie:
            root.append(i.to_xml("identificatie"))

        naam_elem = ET.SubElement(root, "naam")
        naam_elem.text = self.naam

        if self.aggregatieNiveau:
            root.append(self.aggregatieNiveau.to_xml("aggregatieniveau"))

        if self.classificatie:
            root.append(self.classificatie.to_xml("classificatie"))

        if self.trefwoord:
            trefwoord_elem = ET.SubElement(root, "trefwoord")
            trefwoord_elem.text = self.trefwoord

        if self.omschrijving:
            omschrijving_elem = ET.SubElement(root, "omschrijving")
            omschrijving_elem.text = self.omschrijving

        if self.dekkingInTijd:
            root.append(self.dekkingInTijd.to_xml())

        if self.event:
            root.append(self.event.to_xml())

        root.append(self.waardering.to_xml("waardering"))

        if self.isOnderdeelVan:
            root.append(self.isOnderdeelVan.to_xml("isOnderdeelVan"))

        if self.bevatOnderdeel:
            if isinstance(self.bevatOnderdeel, VerwijzingGegevens):
                self.bevatOnderdeel = [self.bevatOnderdeel]
            for b in self.bevatOnderdeel:
                root.append(b.to_xml("bevatOnderdeel"))
        
        if self.aanvullendeMetagegevens:
            if isinstance(self.aanvullendeMetagegevens, VerwijzingGegevens):
                self.aanvullendeMetagegevens = [self.aanvullendeMetagegevens]
            for b in self.aanvullendeMetagegevens:
                root.append(b.to_xml("aanvullendeMetagegevens"))

        root.append(self.archiefvormer.to_xml("archiefvormer"))

        # allow users to pass either a single BeperkingGebruikGegevens object, or a list thereof
        if isinstance(self.beperkingGebruik, BeperkingGebruikGegevens):
            self.beperkingGebruik = [self.beperkingGebruik]

        for b in self.beperkingGebruik:
            root.append(b.to_xml())

        # can you abstract this? this is now double
        # on the other hand, formatting preferences should be handled by e.g. xmllint
        tree = ET.ElementTree(mdto)
        ET.indent(tree, space="    ")  # use 4 spaces as indentation

        return tree


@dataclass
class Bestand:
    """MDTO Bestand class.

    When creating Bestand XML files, it may be more easier to instead use the
    `create_bestand()` convenience function, or to invoke this program as a CLI tool.

    MDTO docs: https://www.nationaalarchief.nl/archiveren/mdto/bestand

    Args:
        identificatie (IdentificatieGegevens): Gegevens waarmee het object geïdentificeerd kan worden
        naam (str): Een betekenisvolle aanduiding waaronder het object bekend is
        omvang (int): Aantal bytes in het bestand
        bestandsformaat (BegripGegevens): Manier waarop de informatie in een computerbestand binair gecodeerd is
        checksum (ChecksumGegevens): Checksum gegevens over het bestand
        isRepresentatieVan (VerwijzingGegevens): Verwijzing naar het informatieobject waarvan het bestand een (deel van een) representatie is
        URLBestand (str, optional): Actuele verwijzing naar het bestand in de vorm van een RFC 3986 conforme URI

    """

    naam: str
    identificatie: IdentificatieGegevens | List[IdentificatieGegevens]
    omvang: int
    bestandsformaat: BegripGegevens
    checksum: ChecksumGegevens | List[ChecksumGegevens]
    isRepresentatieVan: VerwijzingGegevens
    URLBestand: str = None

    def __post_init__(self):
        # check if name is of the right length
        # the getter and setter created weird errors
        if len(self.naam) > MAX_NAAM_LENGTH:
            _warn(
                f"value '{self.naam}' of element 'naam' "
                f"exceeds maximum length of {MAX_NAAM_LENGTH}."
            )

    def to_xml(self) -> ET.ElementTree:
        """
        Transform Bestand into an XML tree with the following structure:

        ```xml
        <MDTO xmlns=…>
            <bestand>
                …
            </bestand>
        </MDTO>
        ```

        Returns:
            ET.ElementTree: XML tree representing Bestand object. This object can be written to a file by calling `.write()`.
        """

        mdto = ET.Element(
            "MDTO",
            attrib={
                "xmlns": "https://www.nationaalarchief.nl/mdto",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd",
            },
        )

        root = ET.SubElement(mdto, "bestand")

        if isinstance(self.identificatie, IdentificatieGegevens):
            self.identificatie = [self.identificatie]

        for i in self.identificatie:
            root.append(i.to_xml("identificatie"))

        naam = ET.SubElement(root, "naam")
        naam.text = self.naam

        omvang = ET.SubElement(root, "omvang")
        # ET wants str types
        omvang.text = str(self.omvang)

        # bestandsformaat can be None if fido detection failed and force is True
        if self.bestandsformaat:
            root.append(self.bestandsformaat.to_xml("bestandsformaat"))

        root.append(self.checksum.to_xml())

        if self.URLBestand:
            url = ET.SubElement(root, "URLBestand")
            url.text = self.URLBestand

        # can be None if XML parsing failed
        if self.isRepresentatieVan:
            root.append(self.isRepresentatieVan.to_xml("isRepresentatieVan"))

        tree = ET.ElementTree(mdto)
        ET.indent(tree, space="    ")  # use 4 spaces as indentation

        return tree

    @property
    def URLBestand(self):
        """Value of MDTO 'URLBestand' tag.

        Valid value: any RFC 3986 compliant URI
        MDTO docs: https://www.nationaalarchief.nl/archiveren/mdto/URLBestand
        """
        return self._URLBestand

    @URLBestand.setter
    def URLBestand(self, url):
        # if url is not set (e.g. when calling Bestand() without the URLBestand argument),
        # it will not be None, but rather an empty "property" object
        if isinstance(url, property) or url is None: # check if empty
            self._URLBestand = None
        elif validators.url(url):
            self._URLBestand = url
        else:
            _warn(f"URL '{url} is malformed.")
            self._URLBestand = url


def detect_verwijzing(informatieobject: TextIO) -> VerwijzingGegevens:
    """
    A Bestand object must contain a reference to a corresponding informatieobject.
    Specifically, it expects an <isRepresentatieVan> tag with the following children:

    1. <verwijzingNaam>: name of the informatieobject
    2. <verwijzingIdentificatie> (optional): reference to the
    informatieobject's ID and source thereof

    This function infers these so-called 'VerwijzingGegevens' by
    parsing the XML of the file `informatieobject`.

    MDTO Docs:
        https://www.nationaalarchief.nl/archiveren/mdto/isRepresentatieVan

    Args:
        informatieobject (TextIO): XML file to infer VerwijzingGegevens from

    Returns:
        `VerwijzingGegevens`, refering to the informatieobject specified by `informatieobject`
    """

    id_gegevens = None
    namespaces = {"mdto": "https://www.nationaalarchief.nl/mdto"}
    tree = ET.parse(informatieobject)
    root = tree.getroot()

    id_xpath = ".//mdto:informatieobject/mdto:identificatie/"

    kenmerk = root.find(id_xpath + "mdto:identificatieKenmerk", namespaces=namespaces)
    bron = root.find(id_xpath + "mdto:identificatieBron", namespaces=namespaces)
    naam = root.find(".//mdto:informatieobject/mdto:naam", namespaces=namespaces)

    # bool(ET.Element) == False, according to the docs
    # So use ¬p and ¬q == ¬(p or q)
    if not (kenmerk is None or bron is None):
        id_gegevens = IdentificatieGegevens(kenmerk.text, bron.text)

    if naam is None:
        _error(f"informatieobject in {informatieobject} " "lacks a <naam> tag.")
    else:
        return VerwijzingGegevens(naam.text, id_gegevens)


def pronominfo(path: str) -> BegripGegevens:
    # FIXME: format more properly
    """Use fido library to generate PRONOM information about a file.
    This information can be used in the <bestandsformaat> tag.

    Args:
        path (str): path to the file to inspect

    Returns:
        ``BegripGegevens`` object with the following properties::
            {
                `begripLabel`: file's PRONOM signature name
                `begripCode`: file's PRONOM ID
                `begripBegrippenLijst`: reference to PRONOM registry
            }
    """

    # Note: fido currently lacks a public API
    # Hence, the most robust solution is to invoke fido as a cli program
    # Upstream issue: https://github.com/openpreserve/fido/issues/94
    # downside is that this is slow, maybe siegfried speeds things up?

    # check if fido program exists
    if not shutil.which("fido"):
        _error(
            "'fido' not found. For installation instructions, "
            "see https://github.com/openpreserve/fido#installation"
        )

    cmd = [
        "fido",
        "-q",
        "-matchprintf",
        "OK,%(info.formatname)s,%(info.puid)s,\n",
        "-nomatchprintf",
        "FAIL",
        path,
    ]

    cmd_result = subprocess.run(
        cmd, capture_output=True, shell=False, text=True, check=True
    )
    stdout = cmd_result.stdout
    stderr = cmd_result.stderr
    returncode = cmd_result.returncode

    # fido prints warnings about empty files to stderr
    if "(empty)" in stderr.lower():
        _warn(f"file {path} appears to be an empty file!")

    # check for errors
    if returncode != 0:
        _warn(f"fido PRONOM detection on file {path} failed with error '{stderr}'.")
    elif stdout.startswith("OK"):
        results = stdout.split("\n")
        if len(results) > 2:  # .split('\n') returns a list of two items
            _log(
                "Info: fido returned more than one PRONOM match "
                f"for file {path}. Selecting the first one."
            )

        # strip "OK" from the output
        results = results[0].split(",")[1:]
        verwijzing = VerwijzingGegevens(verwijzingNaam="PRONOM-register")
        return BegripGegevens(
            begripLabel=results[0],
            begripCode=results[1],
            begripBegrippenlijst=verwijzing,
        )
    else:
        _warn(f"fido failed to detect PRONOM ID of file {path}.")

    # can return None in case PRONOM detection fails and force == True
    return None


def create_bestand(
    infile: TextIO | str,
    identificatiekenmerken: List[str] | str,
    identificatiebronnen: List[str] | str,
    informatieobject: TextIO,
    naam: str = None,
    url: str = None,
    quiet: bool = False,
    force: bool = False,
) -> Bestand:
    """
    Convenience function for creating Bestand objects. The difference between this function
    and calling Bestand() directly is that this function infers most Bestand-related
    information for you, based on the characteristics of `infile`.

    Supply a list of strings to `identificatiekenmerken` and `identificatiebronnen`
    if multiple <identificatie> tags are desired. Otherwise, a single str suffices.

    Args:
        infile (TextIO | str): the file the Bestand object should represent. Can be a path or file-like object
        identificatiekenmerken (List[str] | str): str or list of str for <identificatieKenmerk> tags
        identificatiebronnen (List[str] | str): str or list of str for <identificatieBron> tags
        informatieobject (TextIO | str): path or file-like object that
            represents an MDTO Informatieobject in XML form.
            Used to infer values for <isRepresentatieVan>.
        naam (str, optional): value of <naam>. Defaults to the basename of `infile`
        url (str, optional): value of <URLBestand>
        quiet (bool, optional): silence non-fatal warnings
        force (bool, optional): do not exit when encountering would-be invalid tag values

    Example:
        ```python

        with open('informatieobject_001.xml') as f:
            bestand = create_bestand("vergunning.pdf", '34c5-4379-9f1a-5c378', 'Proza (DMS)', informatieobject=f)
            xml = bestand.to_xml()
        ```
    """
    global _force, _quiet
    _quiet = quiet
    _force = force

    # allow infile to be a path (str)
    infile = _process_file(infile)

    # permit setting kenmerk and bron to a string
    if isinstance(identificatiekenmerken, str):
        identificatiekenmerken = [identificatiekenmerken]
    if isinstance(identificatiebronnen, str):
        identificatiebronnen = [identificatiebronnen]

    if len(identificatiekenmerken) != len(identificatiebronnen):
        _error(
            "number of 'identificatieKenmerk' tags differs from "
            "number of 'identificatieBron' tags"
        )

    ids = [
        IdentificatieGegevens(k, b)
        for k, b in zip(identificatiekenmerken, identificatiebronnen)
    ]

    if not naam:
        naam = os.path.basename(infile.name)

    omvang = os.path.getsize(infile.name)
    bestandsformaat = pronominfo(infile.name)
    checksum = ChecksumGegevens(infile)

    informatieobject = _process_file(informatieobject)
    isrepresentatievan = detect_verwijzing(informatieobject)

    informatieobject.close()
    infile.close()

    return Bestand(
        naam, ids, omvang, bestandsformaat, checksum, isrepresentatievan, url
    )
