import os
import shutil
import sys
import subprocess
import hashlib
from typing import TextIO, List
from datetime import datetime
import lxml.etree as ET
from dataclasses import dataclass
from functools import partial

# Make into an optional dependency?
import validators

# globals
MAX_NAAM_LENGTH = 80
_force, _quiet = False, False


# Helper methods
def _process_file(file_or_filename) -> TextIO:
    """Return file-object if input is already a file.
    Otherwise, assume the argument is a path, and convert
    it to a new file-object.

    Note:
        The returned file-object is always in read-only mode.
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
    """https://www.nationaalarchief.nl/archiveren/mdto/identificatieGegevens

    Args:
        identificatieKenmerk (str): Een kenmerk waarmee een object geïdentificeerd kan worden
        identificatieBron (str): Herkomst van het kenmerk
    """

    identificatieKenmerk: str
    identificatieBron: str

    def to_xml(self, root: str) -> ET.Element:
        """Transform IdentificatieGegevens into XML tree.

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
    """https://www.nationaalarchief.nl/archiveren/mdto/verwijzingsGegevens

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
    """https://www.nationaalarchief.nl/archiveren/mdto/begripGegevens

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


@dataclass
class TermijnGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/termijnGegevens

    Args:
        termijnTriggerStartLooptijd (BegripGegevens, optional): Gebeurtenis waarna de looptijd van de termijn start
        termijnStartdatumLooptijd (str, optional): Datum waarop de looptijd is gestart
        termijnLooptijd (str, optional): Hoeveelheid tijd waarin de termijnEindDatum bereikt wordt
        termijnEinddatum (str, optional): Datum waarop de termijn eindigt
    """

    termijnTriggerStartLooptijd: BegripGegevens = None
    termijnStartdatumLooptijd: str = None
    termijnLooptijd: str = None
    termijnEinddatum: str = None

    def to_xml(self, root: str) -> ET.Element:
        """Transform TermijnGegevens into XML tree.

        Args:
            root (str): name of the new root tag

        Returns:
            ET.Element: XML representation of TermijnGegevens with new root tag
        """
        root = ET.Element(root)

        if self.termijnTriggerStartLooptijd:
            root.append(
                self.termijnTriggerStartLooptijd.to_xml("termijnTriggerStartLooptijd")
            )

        if self.termijnStartdatumLooptijd:
            termijnStartdatumLooptijd = ET.SubElement(root, "termijnStartdatumLooptijd")
            termijnStartdatumLooptijd.text = self.termijnStartdatumLooptijd

        if self.termijnLooptijd:
            termijnLooptijd = ET.SubElement(root, "termijnLooptijd")
            termijnLooptijd.text = self.termijnLooptijd

        if self.termijnEinddatum:
            termijnEinddatum = ET.SubElement(root, "termijnEinddatum")
            termijnEinddatum.text = self.termijnEinddatum

        return root

@dataclass
class ChecksumGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/checksum

    Note: 
        When building Bestand objects, it's recommended to call the convience function `create_bestand()` instead.
        Moreover, if you just need to update a Bestand object's checksum, you should use `create_checksum()`.
    """
    checksumAlgoritme: BegripGegevens
    checksumWaarde: str
    checksumDatum: str

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
    """https://www.nationaalarchief.nl/archiveren/mdto/beperkingGebruik

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
    beperkingGebruikTermijn: TermijnGegevens = None

    def to_xml(self) -> ET.Element:
        """Transform BeperkingGebruikGegevens into XML tree.

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
            root.append(self.beperkingGebruikTermijn.to_xml("beperkingGebruikTermijn"))

        return root


@dataclass
class DekkingInTijdGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/dekkingInTijd

    Args:
        dekkingInTijdType (BegripGegevens): Typering van de periode waar het informatieobject betrekking op heeft
        dekkingInTijdBegindatum (str): Begindatum van de periode waar het informatieobject betrekking op heeft
        dekkingInTijdEinddatum (str, optional): Einddatum van de periode waar het informatieobject betrekking op heeft
    """

    dekkingInTijdType: BegripGegevens
    dekkingInTijdBegindatum: str
    dekkingInTijdEinddatum: str = None

    def to_xml(self) -> ET.Element:
        root = ET.Element("dekkingInTijd")

        root.append(self.dekkingInTijdType.to_xml("dekkingInTijdType"))

        begin_datum_elem = ET.SubElement(root, "dekkingInTijdBegindatum")
        begin_datum_elem.text = self.dekkingInTijdBegindatum

        if self.dekkingInTijdEinddatum:
            eind_datum_elem = ET.SubElement(root, "dekkingInTijdEinddatum")
            eind_datum_elem.text = self.dekkingInTijdEinddatum

        return root


@dataclass
class EventGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/event

    Args:
        eventType (BegripGegevens): Aanduiding van het type event
        eventTijd (str, optional): Tijdstip waarop het event heeft plaatsgevonden
        eventVerantwoordelijkeActor (VerwijzingGegevens, optional): Actor die verantwoordelijk was voor het event
        eventResultaat (str, optional): Beschrijving van het resultaat van het event
    """

    eventType: BegripGegevens
    eventTijd: str = None
    eventVerantwoordelijkeActor: VerwijzingGegevens = None
    eventResultaat: str = None

    def to_xml(self) -> ET.Element:
        root = ET.Element("event")

        root.append(self.eventType.to_xml("eventType"))

        if self.eventTijd:
            event_tijd_elem = ET.SubElement(root, "eventTijd")
            event_tijd_elem.text = self.eventTijd

        if self.eventVerantwoordelijkeActor:
            root.append(
                self.eventVerantwoordelijkeActor.to_xml("eventVerantwoordelijkeActor")
            )

        if self.eventResultaat:
            event_resultaat_elem = ET.SubElement(root, "eventResultaat")
            event_resultaat_elem.text = self.eventResultaat

        return root


@dataclass
class RaadpleeglocatieGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/raadpleeglocatie

    Args:
        raadpleeglocatieFysiek (VerwijzingGegevens, optional): Fysieke raadpleeglocatie van het informatieobject
        raadpleeglocatieOnline (str, optional): Online raadpleeglocatie van het informatieobject; moet een valide URL zijn
    """

    raadpleeglocatieFysiek: VerwijzingGegevens = None
    raadpleeglocatieOnline: str = None

    def to_xml(self):
        root = ET.Element("raadpleeglocatie")

        # raadpleeglocatie may have no children, strangely enough
        if self.raadpleeglocatieFysiek:
            root.append(self.raadpleeglocatieFysiek.to_xml("raadpleeglocatieFysiek"))

        if self.raadpleeglocatieOnline:
            raadpleeglocatie_online_elem = ET.SubElement(root, "raadpleeglocatieOnline")
            raadpleeglocatie_online_elem.text = self.raadpleeglocatieOnline

        return root

    @property
    def raadpleeglocatieOnline(self):
        return self._raadpleeglocatieOnline

    @raadpleeglocatieOnline.setter
    def raadpleeglocatieOnline(self, url: str | List[str]):
        """https://www.nationaalarchief.nl/archiveren/mdto/raadpleeglocatieOnline

        Args:
            url (str): any RFC 3986 compliant URI
        """
        # if url is not set, (e.g. when calling RaadpleegLocatieGegevens() without arguments)
        # it will not be None, but rather an empty "property" object
        if isinstance(url, property) or url is None:  # check if empty
            self._raadpleeglocatieOnline = None
        elif isinstance(url, list) and all(validators.url(u) for u in url):
            self._raadpleeglocatieOnline = url
        elif isinstance(url, str) and validators.url(url):
            self._raadpleeglocatieOnline = url
        else:
            _warn(f"URL '{url}' is malformed.")
            self._raadpleeglocatieOnline = url


@dataclass
class GerelateerdInformatieobjectGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/gerelateerdInformatieobjectGegevens

    Args:
        gerelateerdInformatieobjectVerwijzing (VerwijzingGegevens): Verwijzing naar het gerelateerde informatieobject
        gerelateerdInformatieobjectTypeRelatie (BegripGegevens): Typering van de relatie
    """

    gerelateerdInformatieobjectVerwijzing: VerwijzingGegevens
    gerelateerdInformatieobjectTypeRelatie: BegripGegevens

    def to_xml(self) -> ET.Element:
        root = ET.Element("gerelateerdInformatieobject")

        root.append(
            self.gerelateerdInformatieobjectVerwijzing.to_xml(
                "gerelateerdInformatieobjectVerwijzing"
            )
        )

        root.append(
            self.gerelateerdInformatieobjectTypeRelatie.to_xml(
                "gerelateerdInformatieobjectTypeRelatie"
            )
        )

        return root


@dataclass
class BetrokkeneGegevens:
    """https://www.nationaalarchief.nl/archiveren/mdto/betrokkeneGegevens

    Args:
        betrokkeneTypeRelatie (BegripGegevens): Typering van de betrokkenheid van de actor bij het informatieobject
        betrokkeneActor (VerwijzingGegevens): Persoon of organisatie die betrokken is bij het informatieobject
    """

    betrokkeneTypeRelatie: BegripGegevens
    betrokkeneActor: VerwijzingGegevens

    def to_xml(self) -> ET.Element:
        root = ET.Element("betrokkene")

        root.append(self.betrokkeneTypeRelatie.to_xml("betrokkeneTypeRelatie"))
        root.append(self.betrokkeneActor.to_xml("betrokkeneActor"))

        return root


# TODO: this should be a subclass of a general object class
# TODO: place more restrictions on taal?
@dataclass
class Informatieobject:
    """https://www.nationaalarchief.nl/archiveren/mdto/informatieobject

    Example:

    ```python
    informatieobject = Informatieobject(IdentificatieGegevens(…), naam="Kapvergunning", …)

    xml = informatieobject.to_xml()
    with open("informatieobject.xml", 'w') as output_file:
        xml.write(output_file, xml_declaration=True, short_empty_elements=False)
    ```

    Args:
        naam (str): Betekenisvolle aanduiding waaronder het object bekend is
        identificatie (IdentificatieGegevens | List[IdentificatieGegevens]): Gegevens waarmee het object geïdentificeerd kan worden
        archiefvormer (VerwijzingGegevens | List[VerwijzingGegevens]): Organisatie die verantwoordelijk is voor het opmaken en/of ontvangen van het informatieobject
        beperkingGebruik (BeperkingGebruikGegevens | List[BeperkingGebruikGegevens]): Beperking die gesteld is aan het gebruik van het informatieobject
        waardering (BegripGegevens): Waardering van het informatieobject volgens een selectielijst
        aggregatieniveau (BegripGegevens, optional): Aggregatieniveau van het informatieobject
        classificatie (BegripGegevens, optional): Classificatie van het informatieobject
        trefwoord (str | List[str], optional): Trefwoord dat het informatieobject beschrijft
        omschrijving (str, optional): Omschrijving van het informatieobject
        dekkingInTijd (DekkingInTijdGegevens, optional): Periode waarop het informatieobject betrekking heeft
        dekkingInRuimte (VerwijzingGegevens, optional): Plaats/locatie waar het informatieobject betrekking op heeft
        taal (str, optional): Taal waarin het informatieobject gesteld is
        event (EventGegevens | List[EventGegevens], optional): Gebeurtenis gerelateerd aan het informatieobject
        bewaartermijn (TermijnGegevens, optional): Termijn waarin het informatieobject bewaard dient te worden
        informatiecategorie (BegripGegevens, optional): Informatiecategorie uit een selectie- of hotspotlijst waar de bewaartermijn op gebaseerd is
        bevatOnderdeel (VerwijzingGegevens, optional): Verwijzing naar een ander onderdeel dat deel uitmaakt van het informatieobject
        isOnderdeelVan (VerwijzingGegevens, optional): Bovenliggende aggregatie waar dit informatieobject onderdeel van is
        heeftRepresentatie (VerwijzingGegevens, optional): Verwijzing naar het bestand dat een representatie van het informatieobject is
        aanvullendeMetagegevens (VerwijzingGegevens, optional): Verwijzing naar een bestand dat aanvullende (domeinspecifieke) metagegevens over het informatieobject bevat
        gerelateerdInformatieobject (GerelateerdInformatieobjectGegevens, optional): Informatie over een gerelateerd informatieobject
        betrokkene (BetrokkeneGegevens | List[BetrokkeneGegevens], optional): Persoon of organisatie die relevant was binnen het ontstaan en gebruik van het informatieobject
        activiteit (VerwijzingGegevens, optional): Bedrijfsactiviteit waarbij het informatieobject door de archiefvormer is ontvangen of gemaakt
    """

    naam: str
    identificatie: IdentificatieGegevens | List[IdentificatieGegevens]
    archiefvormer: VerwijzingGegevens | List[VerwijzingGegevens]
    beperkingGebruik: BeperkingGebruikGegevens | List[BeperkingGebruikGegevens]
    waardering: BegripGegevens
    aggregatieniveau: BegripGegevens = None
    classificatie: BegripGegevens = None
    trefwoord: str | List[str] = None
    omschrijving: str = None
    raadpleeglocatie: RaadpleeglocatieGegevens = None
    dekkingInTijd: DekkingInTijdGegevens = None
    dekkingInRuimte: VerwijzingGegevens = None
    taal: str = None
    event: EventGegevens | List[EventGegevens] = None
    bewaartermijn: TermijnGegevens = None
    informatiecategorie: BegripGegevens = None
    bevatOnderdeel: VerwijzingGegevens | List[VerwijzingGegevens] = None
    isOnderdeelVan: VerwijzingGegevens = None
    heeftRepresentatie: VerwijzingGegevens = None
    aanvullendeMetagegevens: VerwijzingGegevens | List[VerwijzingGegevens] = None
    gerelateerdInformatieobject: GerelateerdInformatieobjectGegevens = None
    betrokkene: BetrokkeneGegevens | List[BetrokkeneGegevens] = None
    activiteit: VerwijzingGegevens = None

    def to_xml(self) -> ET.ElementTree:
        """Transform Informatieobject into an XML tree with the following structure:

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

        # construct attributes of <MDTO>
        xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
        nsmap = {
            None: "https://www.nationaalarchief.nl/mdto",  # default namespace (i.e. xmlns=https...)
            "xsi": xsi_ns,
        }

        # create <MDTO>
        mdto = ET.Element("MDTO", nsmap=nsmap)

        # set schemaLocation attribute of <MDTO>
        mdto.set(
            f"{{{xsi_ns}}}schemaLocation",
            "https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd",
        )

        root = ET.SubElement(mdto, "informatieobject")

        # allow users to pass either a single IdentificatieGegevens object, or a list thereof
        if isinstance(self.identificatie, IdentificatieGegevens):
            self.identificatie = [self.identificatie]

        for i in self.identificatie:
            root.append(i.to_xml("identificatie"))

        naam_elem = ET.SubElement(root, "naam")
        naam_elem.text = self.naam

        if self.aggregatieniveau:
            root.append(self.aggregatieniveau.to_xml("aggregatieniveau"))

        if self.classificatie:
            root.append(self.classificatie.to_xml("classificatie"))

        if self.trefwoord:
            # allow users to pass either a single trefwoord, or a list thereof
            if isinstance(self.trefwoord, str):
                self.trefwoord = [self.trefwoord]

            for t in self.trefwoord:
                trefwoord = ET.SubElement(root, "trefwoord")
                trefwoord.text = t

        if self.omschrijving:
            omschrijving_elem = ET.SubElement(root, "omschrijving")
            omschrijving_elem.text = self.omschrijving

        if self.raadpleeglocatie:
            root.append(self.raadpleeglocatie.to_xml())

        if self.dekkingInTijd:
            root.append(self.dekkingInTijd.to_xml())

        if self.dekkingInRuimte:
            root.append(self.dekkingInRuimte.to_xml("dekkingInRuimte"))

        if self.taal:
            taal_elem = ET.SubElement(root, "taal")
            taal_elem.text = self.taal

        if self.event:
            if isinstance(self.event, EventGegevens):
                self.event = [self.event]

            for e in self.event:
                root.append(e.to_xml())

        root.append(self.waardering.to_xml("waardering"))

        if self.bewaartermijn:
            root.append(self.bewaartermijn.to_xml("bewaartermijn"))

        if self.informatiecategorie:
            root.append(self.informatiecategorie.to_xml("informatiecategorie"))

        if self.isOnderdeelVan:
            root.append(self.isOnderdeelVan.to_xml("isOnderdeelVan"))

        if self.bevatOnderdeel:
            if isinstance(self.bevatOnderdeel, VerwijzingGegevens):
                self.bevatOnderdeel = [self.bevatOnderdeel]

            for b in self.bevatOnderdeel:
                root.append(b.to_xml("bevatOnderdeel"))

        if self.heeftRepresentatie:
            root.append(self.heeftRepresentatie.to_xml("heeftRepresentatie"))

        if self.aanvullendeMetagegevens:
            if isinstance(self.aanvullendeMetagegevens, VerwijzingGegevens):
                self.aanvullendeMetagegevens = [self.aanvullendeMetagegevens]
            for b in self.aanvullendeMetagegevens:
                root.append(b.to_xml("aanvullendeMetagegevens"))

        if self.gerelateerdInformatieobject:
            root.append(
                self.gerelateerdInformatieobject.to_xml("gerelateerdInformatieobject")
            )

        root.append(self.archiefvormer.to_xml("archiefvormer"))

        if self.betrokkene:
            # allow users to pass either a single BetrokkeneGegevens object, or a list thereof
            if isinstance(self.betrokkene, BetrokkeneGegevens):
                self.betrokkene = [self.betrokkene]

            for b in self.betrokkene:
                root.append(b.to_xml())

        if self.activiteit:
            root.append(self.activiteit.to_xml("activiteit"))

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
    """https://www.nationaalarchief.nl/archiveren/mdto/bestand

    Note:
        When creating Bestand XML files, it's easier to use the
        `create_bestand()` convenience function instead.

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

        # construct attributes of <MDTO>
        xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
        nsmap = {
            None: "https://www.nationaalarchief.nl/mdto",  # default namespace (i.e. xmlns=https...)
            "xsi": xsi_ns,
        }

        # create <MDTO>
        mdto = ET.Element("MDTO", nsmap=nsmap)

        # set schemaLocation attribute of <MDTO>
        mdto.set(
            f"{{{xsi_ns}}}schemaLocation",
            "https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd",
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
        return self._URLBestand

    @URLBestand.setter
    def URLBestand(self, url: str):
        """https://www.nationaalarchief.nl/archiveren/mdto/URLBestand

        Args:
            url (str): any RFC 3986 compliant URI
        """
        # if url is not set (e.g. when calling Bestand() without the URLBestand argument),
        # it will not be None, but rather an empty "property" object
        if isinstance(url, property) or url is None:  # check if empty
            self._URLBestand = None
        elif validators.url(url):
            self._URLBestand = url
        else:
            _warn(f"URL '{url} is malformed.")
            self._URLBestand = url


def detect_verwijzing(informatieobject: TextIO) -> VerwijzingGegevens:
    """A Bestand object must contain a reference to a corresponding informatieobject.
    Specifically, it expects an <isRepresentatieVan> tag with the following children:

    1. <verwijzingNaam>: name of the informatieobject
    2. <verwijzingIdentificatie> (optional): reference to the
    informatieobject's ID and source thereof

    This function infers these so-called 'VerwijzingGegevens' by
    parsing the XML of the file `informatieobject`.

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
    """Convenience function for creating Bestand objects. The difference between this function
    and calling Bestand() directly is that this function infers most Bestand-related
    information for you, based on the characteristics of `infile`.

    Supply a list of strings to `identificatiekenmerken` and `identificatiebronnen`
    if multiple <identificatie> tags are desired. Otherwise, a single str suffices.

    Args:
        infile (TextIO | str): the file the Bestand object should represent
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
    checksum = create_checksum(infile)

    informatieobject = _process_file(informatieobject)
    isrepresentatievan = detect_verwijzing(informatieobject)

    informatieobject.close()
    infile.close()

    return Bestand(
        naam, ids, omvang, bestandsformaat, checksum, isrepresentatievan, url
    )


def create_checksum(
    file_or_filename: TextIO | str, algorithm: str = "sha256"
) -> ChecksumGegevens:
    """Convience function for creating ChecksumGegegevens objects.

    Takes a file-like object or path to file, and then generates the requisite
    checksum metadata (i.e.  `checksumAlgoritme`, `checksumWaarde`, and
    `checksumDatum`) from that file.

    Example:
    ```python
    pdf_checksum = create_checksum('document.pdf')
    # create ChecksumGegevens with a 512 bits instead of a 256 bits checksum
    jpg_checksum = create_checksum('scan-003.jpg', algorithm="sha512")
    ```

    Args:
        infile (TextIO | str): file-like object to generate checksum data for
        algorithm (str, optional): checksum algorithm to use; defaults to sha256.
         For valid values, see https://docs.python.org/3/library/hashlib.html

    Returns:
        ChecksumGegevens: checksum metadata from `file_or_filename`
    """
    infile = _process_file(file_or_filename)
    verwijzing = VerwijzingGegevens(
        verwijzingNaam="Begrippenlijst ChecksumAlgoritme MDTO"
    )

    checksumAlgoritme = BegripGegevens(
        begripLabel=algorithm.upper().replace("SHA", "SHA-"),
        begripBegrippenlijst=verwijzing,
    )

    # file_digest() expects a file in binary mode, hence `infile.buffer.raw`
    # FIXME: this value is not the same on each call?
    checksumWaarde = hashlib.file_digest(infile.buffer.raw, algorithm).hexdigest()

    checksumDatum = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    return ChecksumGegevens(checksumAlgoritme, checksumWaarde, checksumDatum)


# TODO: this type annotation should be redone when the abstract Object class is implemented
# Q: should this also accept file objects?
def from_file(xmlfile: str) -> Informatieobject | Bestand:
    """Construct a Informatieobject/Bestand object from a MDTO XML file.

    Note:
        When `xmlfile` is invalid MDTO, this function will probably throw an error.

    Example:

    ```python
    import mdto

    informatieobject = mdto.from_file("Voorbeeld Archiefstuk Informatieobject.xml")

    # edit the informatie object
    informatieobject.naam = "Verlenen kapvergunning Flipje's Erf 15 Tiel"

    # save it to a new file
    xml = informatieobject.to_xml()
    with open("Nieuw informatieobject.xml", 'w') as output_file:
        xml.write(output_file, xml_declaration=True, short_empty_elements=False)
    ```

    Args:
        filename (str): The MDTO XML file to construct an Informatieobject/Bestand from

    Returns:
        Informatieobject | Bestand: A new MDTO object
    """

    # Parsers:
    def parse_text(node) -> str:
        return node.text

    def parse_int(node) -> int:
        return int(node.text)

    def parse_identificatie(node) -> IdentificatieGegevens:
        return IdentificatieGegevens(
            node[0].text,
            node[1].text,
        )

    # this is measurably faster than the elem_to_mdto variant
    def parse_verwijzing(node) -> VerwijzingGegevens:
        if len(node) == 1:
            return VerwijzingGegevens(node[0].text)
        else:
            return VerwijzingGegevens(
                node[0].text,
                parse_identificatie(node[1]),
            )

    def elem_to_mdto(elem: ET.Element, mdto_class: classmethod, mdto_xml_parsers: dict):
        """Construct MDTO class from given XML element, using parsers specified in
        mdto_xml_parsers.

        Returns:
            MDTO instance: a initialized MDTO instance of type `mdto_class`
        """
        # initialize dictionary of keyword arguments (to be passed to MDTO class constructor)
        constructor_args = {mdto_field: [] for mdto_field in mdto_xml_parsers}

        for child in elem:
            mdto_field = child.tag.removeprefix(
                "{https://www.nationaalarchief.nl/mdto}"
            )
            # retrieve parser
            xml_parser = mdto_xml_parsers[mdto_field]
            # add value of parsed child element to class constructor args
            constructor_args[mdto_field].append(xml_parser(child))

        for argname, value in constructor_args.items():
            # Convert empty argument lists into None values
            if len(value) == 0:
                constructor_args[argname] = None
            # Convert one-itemed argument lists to non-lists
            elif len(value) == 1:
                constructor_args[argname] = value[0]

        return mdto_class(**constructor_args)

    begrip_parsers = {
        "begripLabel": parse_text,
        "begripCode": parse_text,
        "begripBegrippenlijst": parse_verwijzing,
    }
    parse_begrip = lambda e: elem_to_mdto(e, BegripGegevens, begrip_parsers)

    termijn_parsers = {
        "termijnTriggerStartLooptijd": parse_begrip,
        "termijnStartdatumLooptijd": parse_text,
        "termijnLooptijd": parse_text,
        "termijnEinddatum": parse_text,
    }
    parse_termijn = lambda e: elem_to_mdto(e, TermijnGegevens, termijn_parsers)

    beperking_parsers = {
        "beperkingGebruikType": parse_begrip,
        "beperkingGebruikNadereBeschrijving": parse_text,
        "beperkingGebruikDocumentatie": parse_verwijzing,
        "beperkingGebruikTermijn": parse_termijn,
    }
    parse_beperking = lambda e: elem_to_mdto(
        e, BeperkingGebruikGegevens, beperking_parsers
    )

    raadpleeglocatie_parsers = {
        "raadpleeglocatieFysiek": parse_verwijzing,
        "raadpleeglocatieOnline": parse_text,
    }
    parse_raadpleeglocatie = lambda e: elem_to_mdto(
        e, RaadpleeglocatieGegevens, raadpleeglocatie_parsers
    )

    dekking_in_tijd_parsers = {
        "dekkingInTijdType": parse_begrip,
        "dekkingInTijdBegindatum": parse_text,
        "dekkingInTijdEinddatum": parse_text,
    }
    parse_dekking_in_tijd = lambda e: elem_to_mdto(
        e, DekkingInTijdGegevens, dekking_in_tijd_parsers
    )

    event_parsers = {
        "eventType": parse_begrip,
        "eventTijd": parse_text,
        "eventVerantwoordelijkeActor": parse_verwijzing,
        "eventResultaat": parse_text,
    }
    parse_event = lambda e: elem_to_mdto(e, EventGegevens, event_parsers)

    gerelateerd_informatieobject_parsers = {
        "gerelateerdInformatieobjectVerwijzing": parse_verwijzing,
        "gerelateerdInformatieobjectTypeRelatie": parse_begrip,
    }
    parse_gerelateerd_informatieobject = lambda e: elem_to_mdto(
        e, GerelateerdInformatieobjectGegevens, gerelateerd_informatieobject_parsers
    )

    betrokkene_parsers = {
        "betrokkeneTypeRelatie": parse_begrip,
        "betrokkeneActor": parse_verwijzing,
    }
    parse_betrokkene = lambda e: elem_to_mdto(e, BetrokkeneGegevens, betrokkene_parsers)

    checksum_parsers = {
        "checksumAlgoritme": parse_begrip,
        "checksumWaarde": parse_text,
        "checksumDatum": parse_text,
    }
    parse_checksum = lambda e: elem_to_mdto(e, ChecksumGegevens, checksum_parsers)

    informatieobject_parsers = {
        "naam": parse_text,
        "identificatie": parse_identificatie,
        "aggregatieniveau": parse_begrip,
        "classificatie": parse_begrip,
        "trefwoord": parse_text,
        "omschrijving": parse_text,
        "raadpleeglocatie": parse_raadpleeglocatie,
        "dekkingInTijd": parse_dekking_in_tijd,
        "dekkingInRuimte": parse_verwijzing,
        "taal": parse_text,
        "event": parse_event,
        "waardering": parse_begrip,
        "bewaartermijn": parse_termijn,
        "informatiecategorie": parse_begrip,
        "isOnderdeelVan": parse_verwijzing,
        "bevatOnderdeel": parse_verwijzing,
        "heeftRepresentatie": parse_verwijzing,
        "aanvullendeMetagegevens": parse_verwijzing,
        "gerelateerdInformatieobject": parse_gerelateerd_informatieobject,
        "archiefvormer": parse_verwijzing,
        "betrokkene": parse_betrokkene,
        "activiteit": parse_verwijzing,
        "beperkingGebruik": parse_beperking,
    }
    parse_informatieobject = lambda e: elem_to_mdto(
        e, Informatieobject, informatieobject_parsers
    )

    bestand_parsers = {
        "naam": parse_text,
        "identificatie": parse_identificatie,
        "omvang": parse_int,
        "checksum": parse_checksum,
        "bestandsformaat": parse_begrip,
        "URLBestand": parse_text,
        "isRepresentatieVan": parse_verwijzing,
    }
    parse_bestand = lambda e: elem_to_mdto(e, Bestand, bestand_parsers)

    # read xmlfile
    tree = ET.parse(xmlfile)
    root = tree.getroot()
    children = list(root[0])

    # check if object type is Bestand or Informatieobject
    object_type = root[0].tag.removeprefix("{https://www.nationaalarchief.nl/mdto}")

    if object_type == "informatieobject":
        return parse_informatieobject(children)
    elif object_type == "bestand":
        return parse_bestand(children)
    else:
        raise ValueError(
            f"Unexpected first child <{object_type}> in <MDTO>: "
            "expected <informatieobject> or <bestand>."
        )
