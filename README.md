`mdto.py` is een python library die helpt bij het maken van MDTO XML bestanden. Denk bijvoorbeeld aan het semi-automatisch genereren van technische metagegevens, of wat in MDTO het objectsoort 'Bestand' wordt genoemd:

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

# 💿 Installatie

## Afhankelijkheden


* Python 3.11 of nieuwer.
* Sommige functies van `mdto.py` werken alleen als het programma `fido` in je `PATH` staat. Als je de instructies hieronder volgt gebeurd dit automatisch.

## Systeem-brede installatie

``` shell
git clone https://github.com/Regionaal-Archief-Rivierenland/mdto.py
cd mdto.py
sudo pip install . # Windows gebruikers kunnen "sudo" hier weglaten
```

## Binnen een virtual environment

<details>
<summary>Windows</summary>

``` shell
git clone https://github.com/Regionaal-Archief-Rivierenland/mdto.py
cd mdto.py
python -m venv mdto_env
mdto_env\Scripts\activate
pip install .
```
</details>

<details>
<summary>Linux/WSL/*nix</summary>

``` shell
git clone https://github.com/Regionaal-Archief-Rivierenland/mdto.py
cd mdto.py/
python -m venv mdto_env
source mdto_env/bin/activate
pip install .
```
</details>

# 📖 `mdto.py` als python library

## XML bestanden bouwen

De primaire doelstellingen van `mdto.py` is het versimpelen van het bouwen van MDTO XMLs via python. Om enkele voorbeelden te geven:

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

# schrijf informatieobject naar een bestand
xml = informatieobject.to_xml()
with open("informatieobject.xml", 'w') as output_file:
    xml.write(output_file, xml_declaration=True, short_empty_elements=False)
```

`mdto.py` zorgt er voor dat al deze informatie in de juiste volgorde in de XML terechtkomt — de output bestanden zijn altijd 100% valide MDTO.

In tegenstelling tot python's ingebouwde XML library [`xml.etree`](https://docs.python.org/3/library/xml.etree.elementtree.html) kun je het bovenstaand `informatieobject` gemakkelijk inspecteren en veranderen, bijvoorbeeld via `print()`:

``` python-console
>>> print(informatieobject)
Informatieobject(naam='Verlenen kapvergunning Hooigracht 21 Den Haag',  identificatie=IdentificatieGegevens(identificatieKenmerk='Informatieobject-4661a-5a3526fh654ee', identificatieBron='Proza (OCW-DMS)', ...)
>>> informatieobject.naam = informatieobject.naam.upper() # waardes zijn gemakkelijk aan te passen
>>> print(informatieobject.naam)
'VERLENEN KAPVERGUNNING HOOIGRACHT 21 DEN HAAG'
```

Je kan op een vergelijkbare wijze Bestand objecten bouwen via de `Bestand()` class. Het is vaak echter simpeler om hiervoor de _convience_ functie `create_bestand()` te gebruiken, omdat deze veel gegevens, zoals PRONOM informatie en checksums, automatisch voor je aanmaakt:


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

Het resulterende XML bestand bevat vervolgens de correcte `<omvang>`, `<bestandsformaat>`, `<checksum>` , en `<isRepresentatieVan>` tags. `<URLBestand>` tags kunnen ook worden aangemaakt worden via de optionele `url=` parameter van `create_bestand()`. URLs worden automatisch gevalideerd via de [validators python library](https://pypi.org/project/validators/).

## XML bestanden inlezen

`mdto.py` kan ook MDTO bestanden inlezen en naar python MDTO objecten omzetten via de `from_file` functie.

Stel bijvoorbeeld dat je alle checksums van Bestand XML bestanden wilt updaten:

``` python
import mdto
import glob
import os

# Aangenomen dat je mapstructuur er zo uitziet:
# mdto_collectie/
# ├── Kapvergunning/
# │   ├── 19880405KapvergunningHoogracht.bestand.mdto.xml
# │   ├── 19880405KapvergunningHoogracht.mdto.xml
# │   └── 19880405KapvergunningHoogracht.pdf
# └── Verslag/
#     ├── 19880409Verslag.mdto.bestand.xml
#     ├── 19880409Verslag.mdto.xml
#     └── 19880409Verslag.pdf


# itereer door alle Bestand XMLs:
for bestand_xml in glob.glob('**/*.bestand.mdto.xml', recursive=True):
    bestand_obj = mdto.from_file(bestand_xml)

    # vind naam + path van het te updaten bestand
    filename = bestand.naam
    path = os.path.dirname(bestand_xml) + "/"

    # maak een nieuwe checksum
    bestand.checksum = mdto.create_checksum(path + filename)

    # schrijf geüpdatet Bestand object terug naar een XML file
    xml = bestand.to_xml()
    with open(bestand_xml, 'w') as output_file:
        xml.write(output_file, xml_declaration=True, short_empty_elements=False)
```

## Autocompletion & documentatie in je teksteditor/IDE

`mdto.py` bevat docstrings, zodat teksteditors/IDEs je kunnen ondersteunen met documentatie popups en vensters. Handig als je even niet meer wat een MDTO element precies doet.

[doc-popup.webm](https://github.com/Regionaal-Archief-Rivierenland/mdto/assets/10417027/de41c4e5-900d-48c3-b04b-57dc703e201e)

Autocompletition werkt natuurlijk ook:

[autocompletion-cast.webm](https://github.com/Regionaal-Archief-Rivierenland/mdto/assets/10417027/da6ffff7-132e-481c-b3a0-fd1674fd5da7)

<!-- TODO: sectie/link naar het gebruik van mdto.py (of: het toekomstige programma 'bestand') in een commandline omgeving -->
