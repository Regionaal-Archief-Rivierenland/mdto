`mdto.py` helpt bij het maken van MDTO XML bestanden. Het programma kan op twee manieren worden ingezet; als python library, en als commandline interface (CLI) tool voor het genereren van [MDTO Bestand](https://www.nationaalarchief.nl/archiveren/mdto/metagegevensschema/attribuutspecificaties/klassen/bestand) objecten. 

Op dit moment is `mdto.py` vooral nuttig om automatisch technische metagegevens mee te genereren, of wat binnen MDTO een Bestand object heet:

``` xml
<?xml version='1.0' encoding='UTF-8'?>
<MDTO xmlns="https://www.nationaalarchief.nl/mdto" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd">
    <bestand>
        <identificatie>
            <identificatieKenmerk>345c-4379</identificatieKenmerk>
            <identificatieBron>Corsa</identificatieBron>
        </identificatie>
        <naam>bouwtekening-003.jpg</naam>
        <omvang>1089910</omvang>
        <bestandsformaat>
            <begripLabel>JPEG File Interchange Format</begripLabel>
            <begripCode>fmt/43</begripCode>
            <begripBegrippenlijst>
                <verwijzingNaam>PRONOM-register</verwijzingNaam>
            </begripBegrippenlijst>
        </bestandsformaat>
        <checksum>
            <checksumAlgoritme>
                <begripLabel>SHA-256</begripLabel>
                <begripBegrippenlijst>
                    <verwijzingNaam>Begrippenlijst ChecksumAlgoritme MDTO</verwijzingNaam>
                </begripBegrippenlijst>
            </checksumAlgoritme>
            <checksumWaarde>857ee09fb53f647b16b1f96aba542ace454cd6fc52c9844d4ddb8218c5d61b6c</checksumWaarde>
            <checksumDatum>2024-02-15T16:15:33</checksumDatum>
        </checksum>
        <URLBestand>https://www.example.com/bouwtekening-003.jpg</URLBestand>
        <isRepresentatieVan>
            <verwijzingNaam>Bouwtekening polderstaat</verwijzingNaam>
            <verwijzingIdentificatie>
                <identificatieKenmerk>Informatieobject-4661a-5a3526</identificatieKenmerk>
                <identificatieBron>Corsa</identificatieBron>
            </verwijzingIdentificatie>
        </isRepresentatieVan>
    </bestand>
</MDTO>
```

# Installatie 

## Afhankelijkheden

Om dit programma te gebruiken heb je het volgende nodig:

  * Python 3.11 of nieuwer
  * [fido](https://github.com/openpreserve/fido) (voor pronom detectie)
  * De [validators python library](https://pypi.org/project/validators/) (voor het valideren van URLS)
  
De laatste twee afhankelijkheden kunnen bijv. via pip geinstalleerd worden:

```shell
pip install opf-fido validators
```

De `fido` binary moet in je `PATH` staan.

## Installatie van `mdto.py`

**TODO**

# `mdto.py` als python library

## XML bestanden bouwen

Een van de doelstellingen van `mdto.py` is het versimpelen van het bouwen van MDTO XMLs via python. Om enkele voorbeelden te geven:

``` python
from mdto import *

# maak identificatiekenmerk element
informatieobject_id = IdentificatieGegevens("Informatieobject-4661a-5a3526fh654ee", "Proza (OCW-DMS)")

# maak waardering element
waardering = BegripGegevens(begripLabel="Tijdelijk te bewaren",
                            begripCode="V",
                            begripBegrippenlijst=VerwijzingGegevens("Begrippenlijst Waarderingen MDTO"))

# maak beperkingGebruik element
# beperkingGebruikType verwacht een begrip label (bijv. 'Auteurswet'), en een verwijzing naar een begrippenlijst
beperkingType = BegripGegevens("Auteurswet", VerwijzingGegevens("Gemeente Den Haag zaaksysteem begrippenlijst"))
beperkingGebruik = BeperkingGebruikGegevens(beperkingGebruikType=beperkingType)

# maak informatieobject op basis van deze gegevens 
informatieobject = Informatieobject(identificatie = informatieobject_id,
                 naam = "Verlenen kapvergunning Hooigracht 21 Den Haag",
                 waardering = waardering,
                 archiefvormer = VerwijzingGegevens("'s-Gravenhage"),
                 beperkingGebruik = beperkingGebruik)
                 
# schrijf informatie object naar een bestand
xml = informatieobject.to_xml()
with open("informatieobject.xml", 'w') as output_file:
    xml.write(output_file, xml_declaration=True, short_empty_elements=False)
```

`mdto.py` zorgt er voor dat al deze informatie in de juiste volgorde in de XML terechtkomt — de output bestanden zijn altijd 100% valide MDTO.

In tegenstelling tot python's ingebouwde XML library [`xml.etree`](https://docs.python.org/3/library/xml.etree.elementtree.html) kun je het bovenstaand `informatieobject` gemakkelijk inspecteren en veranderen, bijvoorbeeld via `print()`:

``` python-console
>>> print(informatieobject)
Informatieobject(naam='Verlenen kapvergunning Hooigracht 21 Den Haag',  identificatie=IdentificatieGegevens(identificatieKenmerk='Informatieobject-4661a-5a3526fh654ee', identificatieBron='Proza (OCW-DMS)', ...)
>>> informatieobject.naam = informatieobject.naam.upper() # waardes zijn modificeerbaar
>>> print(informatieobject.naam)
'VERLENEN KAPVERGUNNING HOOIGRACHT 21 DEN HAAG'
```

Je kan op een vergelijkbare wijze Bestand objecten bouwen via de `Bestand()` class. Het is echter meestal simpeler om hiervoor de convience functie `create_bestand()` voor te gebruiken, omdat deze veel gegevens, zoals PRONOM informatie en checksums, automatisch voor je aanmaakt:


```python
from mdto import *

# 'informatieobject_001.xml' is het informatieobject waar het Bestand object een representatie van is 
with open('informatieobject_001.xml') as info_object:
    bestand = create_bestand("vergunning.pdf", '34c5-4379-9f1a-5c378', 'Proza (DMS)', representatievan=info_object)

xml = bestand.to_xml()

# Schrijf xml naar bestand
with open("bestand.xml", 'w') as output_file:
    xml.write(output_file, xml_declaration=True, short_empty_elements=False)
```

Het resulterende XML bestand bevat vervolgens de correcte `<omvang>`, `<bestandsformaat>`, `<checksum>` , en `<isRepresentatieVan>` tags. `<URLBestand>` tags kunnen ook worden aangemaakt worden via de optionele `url=` parameter van `create_bestand()`. URLS worden automatisch gevalideerd via de [validators python library](https://pypi.org/project/validators/).

## Autocompletion & documentatie in je teksteditor/IDE

`mdto.py` bevat docstrings, zodat teksteditors/IDEs je kunnen ondersteunen met documentatie popups en vensters. Handig als je even niet meer wat een MDTO element precies doet.

Autocompletition werkt natuurlijk ook: 

# `mdto.py` als CLI programma

`mdto.py` kan ook worden aangeroepen als commandline programma om MDTO Bestand-objecten mee te genereren. Dit kan handig zijn als je een hele batch aan Bestand XMLs moet genereren, of snel een test bestand wilt aanmaken. Enige nadeel is wel dat de bijhorende Informatieobject XML bestanden al moeten bestaan.


`mdto.py` schrijft standaard naar STDOUT (i.e. je terminal). Dit omdat de output zo vervolgens doorgegeven kan worden aan tools zoals `xmllint`:

``` shell
$ ./mdto.py kapvergunning.pdf --identificatiekenmerk 345c-4379 --identificatiebron Corsa --informatieobject infobj.xml | xmllint --schema MDTO-XML1.0.1.xsd --format
<?xml version="1.0" encoding="utf-8"?>
<MDTO xmlns="https://www.nationaalarchief.nl/mdto" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://www.nationaalarchief.nl/mdto https://www.nationaalarchief.nl/mdto/MDTO-XML1.0.1.xsd">
  <bestand>
    <identificatie>
      <identificatieKenmerk>345c-4379</identificatieKenmerk>
      <identificatieBron>Corsa</identificatieBron>
    </identificatie>
    <naam>kapvergunning.pdf</naam>
    <omvang>243768</omvang>
    <bestandsformaat>
      <begripLabel>Acrobat PDF 1.5 - Portable Document Format</begripLabel>
      <begripCode>fmt/19</begripCode>
      <begripBegrippenlijst>
        <verwijzingNaam>PRONOM-register</verwijzingNaam>
      </begripBegrippenlijst>
    </bestandsformaat>
    ...
  </bestand>
</MDTO>
- validates # STDIN is valide XML!
```

De output van `mdto.py` kan naar een bestand worden geschreven via shell redirection, of via de `-o` flag:

``` shell
# Shell redirection:
$ ./mdto.py input.pdf ... > output_file.xml
# Via de -o/--output flag:
$ ./mdto.py input.pdf   --identificatiekenmerk 5678-abcd ... -o  output_file.xml
```

Voor verdere gebruiksinstructies en een volledige lijst aan CLI opties, zie `mdto --help`:

``` shell
$ mdto --help
usage: mdto.py [-h] --identificatiekenmerk KENMERK --identificatiebron BRON --informatieobject INFORMATIEOBJECT.xml
               [--output [OUTPUT.xml]] [--url URL] [--naam NAAM] [--quiet] [--force]
               FILE

Create a 'MDTO Bestand' .xml file based on FILE. The value of most XML tags will be inferred automatically, but some need to be specified manually.

Example: mdto img001.jpg --identificatiekenmerk 34c5-43a --identificatiebron "Corsa (DMS)" --informatieobject 103.xml

positional arguments:
  FILE                  file for which a MDTO Bestand .xml file should be generated

options:
  -h, --help            show this help message and exit
  --identificatiekenmerk KENMERK, -k KENMERK
                        value of <identificatieKenmerk>. Can be specified multiple times
  --identificatiebron BRON, -b BRON
                        value of <identificatieBron>. Can be specified multiple times
  --informatieobject INFORMATIEOBJECT.xml, -O INFORMATIEOBJECT.xml
                        path to corresponding informatieobject. Used to infer values of <isRepresentatieVan>
  --output [OUTPUT.xml], -o [OUTPUT.xml]
                        file to write to (default: print to stdout)
  --url URL, -u URL     value of <URLBestand>. Needs to be a RFC 3986 compliant URI
  --naam NAAM, -n NAAM  override <naam> with custom value
  --quiet, -q           silence non-fatal warnings
  --force, -f           do not exit when a tag's value conflicts with the MDTO spec. Might produce non-compliant files

For more information, see https://www.nationaalarchief.nl/archiveren/mdto/bestand
```
