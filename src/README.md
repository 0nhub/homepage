# Gabriel Sgroi — Website

Statische Website mit dem Erscheinungsbild der ursprünglichen Menu-Launcher-Seite: Systemschrift, weißer Hintergrund, hellgraue Flächen, blaue Aktionen und transparente Navigation. Keine externen Schriftarten, Frameworks, Tracker oder Laufzeit-Abhängigkeiten.

## Seitenstruktur

Im Projektordner liegen nur `index.html`, `error-page.html` und der Ordner `src/`. Alles andere (Seiten, Assets, Build) liegt in `src/`.

| URL | Inhalt |
| --- | --- |
| `/` | Englische Startseite |
| `/error-page.html` | Fehlerseite |
| `/src/de/` | Deutsche Startseite |
| `/src/projects/menu-launcher/` | Menu Launcher mit Originalbildern und Video |
| `/src/projects/menu-2fa/` | Menu 2FA Produktseite |
| `/src/legal/` | Übersicht der rechtlichen Seiten |
| `/src/legal/imprint/` | Anbieterkennzeichnung: EN Imprint, DE Impressum |
| `/src/legal/privacy/` | Gemeinsame, produktunabhängige Datenschutzseite |
| `/src/legal/terms/` | Gemeinsame, produktunabhängige Nutzungsbedingungen |
| `/src/Support/` | Gemeinsamer Kontakt und Hilfeartikel, nach App gruppiert |
| `/src/apps/` | Ehrliche Zwischenlösung, bis echte App-Store-URLs vorliegen |

Verzeichnisse mit `index.html` funktionieren auf gewöhnlichem statischem Hosting, ohne clientseitiges Routing. Der Webserver ergänzt bei `/legal/privacy` normalerweise den abschließenden Slash.

## Support-Artikel

Hilfeartikel liegen in AppBackend und werden beim Build in die Support-Seite übernommen. In der Tabelle:

- `title` (`name`): Fragetitel
- `position` (`age`): Reihenfolge innerhalb der App, kleinere Zahl zuerst
- `file` (`attachment`): Screenshot
- `content`: Antworttext
- `application`: App-Name, z. B. `Menu Launcher` oder `Menu 2FA`

Nach Änderungen in AppBackend:

```sh
python3 src/scripts/build.py
```

Die öffentliche Seite enthält keinen Schreibschlüssel. Lesen der Tabelle ist öffentlich; der API-Key bleibt nur für das Bearbeiten in AppBackend. Die Support-Seite übernimmt die Artikel beim Build und aktualisiert sie zusätzlich im Browser, sobald JavaScript verfügbar ist.

## Bearbeiten und Vorschau

```sh
python3 src/scripts/build.py
python3 src/scripts/check.py
python3 -m http.server 8000 --bind 127.0.0.1
```

Danach `http://127.0.0.1:8000/` öffnen. Über HTTP testen, nicht per Doppelklick: alle Assets und internen Links sind vom Domain-Root aus adressiert.

- `src/templates/layout.html`: gemeinsamer Header, Footer und Metadaten.
- `src/pages/*.html`: Inhalte der einzelnen Seiten.
- `src/data/i18n.json`: Texte für Englisch und Deutsch (Header, Footer, Metadaten).
- `src/data/projects.json`: Projektnamen, Beschreibung, Status, Icon und App-Store-URL.
- `src/assets/css/styles.css`: zentrale Styles inklusive Mobilansicht.
- `src/assets/js/main.js`: mobiles Menü und Galerie; alle Inhalte, Links und FAQs funktionieren auch ohne JavaScript.
- `src/assets/images/` und `src/assets/media/`: zentral verwaltete Produktmedien.

`index.html` und `error-page.html` liegen im Root. Alle anderen HTML-Seiten werden unter `src/` generiert. Änderungen dort würden beim nächsten Build überschrieben. Es wird nur beim Bearbeiten gebaut; der Hoster braucht kein Python.

Ein neues Projekt in `src/data/projects.json` aufnehmen und `src/pages/<slug>.html` anlegen. Es erscheint automatisch in der Projektübersicht. Für die Hauptpublikation `featured_project` in `site.json` sowie die passende Überschrift in `src/pages/home.html` setzen. Die erste Publikation ist mangels veröffentlichter Datumsangaben vorerst Menu Launcher.

## Bestehende Links

`/Impressum/`, `/Privacy/` und `/Terms/` leiten auf die neuen Pfade unter `/legal/` weiter. Alle bisherigen `/soft/menu-*.html`, `/soft/privacy-menu-*.html`, `/soft/terms-menu-*.html` und `/soft/support-menu-*.html` leiten auf die aktuellen Projekt-, Legal- und Support-Seiten weiter. Für die bisherigen Links ohne Dateiendung existieren ebenfalls Verzeichnisse mit Weiterleitungsseiten. Ein normaler Link ist als Fallback enthalten; JavaScript ist für Weiterleitungen nicht nötig.

`soft/` enthält keine eigenen Inhalte mehr, nur diese Weiterleitungen für bestehende App-Links.

Für Apache wird zusätzlich `.htaccess` mit HTTP-301-Weiterleitungen erzeugt. `_redirects` bietet die entsprechenden Regeln für kompatible statische Hoster.

## Vor der Veröffentlichung offen

- Die echte App-Store-Entwicklerprofil-URL in `site.json` eintragen. Dann führt der Header automatisch direkt dorthin.
- Die echte Menu-Launcher-Listing-URL in `projects.json` eintragen. Der bisherige Eintrag `https://apps.apple.com/app/menulauncher` war nicht verifizierbar und wird nicht als gültiger Download angeboten.
- Menu-2FA-Status, Funktionen und Store-Link bei Veröffentlichung bestätigen. Screenshots und Demovideo können unter `src/assets/images/menu-2fa/` bzw. `src/assets/media/` ergänzt werden.
- Name, Anschrift und bestehende Mailadresse aus der bisherigen Seite bestätigen; bei Bedarf eine gemeinsame Supportadresse eintragen.
- Privacy und Terms sind sichtbare **Entwürfe**, keine rechtliche Freigabe. Hosting- und Mailanbieter, Aufbewahrungsfristen, mögliche Übermittlungen und alle tatsächlichen App-Datenflüsse ergänzen. Dieselbe Privacy-URL kann für mehrere Apps verwendet werden; ihr Inhalt muss die jeweilige Verarbeitung tatsächlich abdecken.
- Die Terms basieren auf den bisherigen 37 Menu-Launcher-Abschnitten; Produktbezüge wurden verallgemeinert bzw. als bedingte Funktionen formuliert. Vertragsbedingungen und deren wirksame Einbeziehung rechtlich prüfen lassen. Für eine eigene App-Store-EULA insbesondere die vollständigen Entwickler-Kontaktdaten inklusive der von Apple genannten Telefonnummer und den Gewährleistungsabschnitt prüfen.
- Ausführlichere persönliche Angaben ergänzen, wenn vorhanden.

Zur Orientierung geprüft: [§ 5 DDG](https://www.gesetze-im-internet.de/ddg/__5.html), [DSGVO](https://eur-lex.europa.eu/eli/reg/2016/679/oj), [Apple-Mindestbedingungen für eigene EULAs](https://www.apple.com/legal/internet-services/itunes/dev/minterms/), [Apple-Standard-EULA](https://www.apple.com/legal/internet-services/itunes/dev/stdeula/). Diese Verweise ersetzen keine individuelle Rechtsprüfung.

## Hosting

Die vorhandene statische Architektur und Domain bleiben erhalten. Es wurde kein neues Hosting-Projekt angelegt, kein DNS geändert und nichts veröffentlicht. Für den bestehenden Hoster sind `index.html`, `error-page.html`, `src/` und gegebenenfalls `.htaccess` bzw. `_redirects` relevant.

Die Originaldateien wurden vor der Umstellung zusätzlich unter `/tmp/sgroi-before-restructure/` gesichert; dieses temporäre Verzeichnis ist kein dauerhaftes Backup.
