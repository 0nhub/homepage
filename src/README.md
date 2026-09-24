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
| `/contact/` | Kontakt-Themenübersicht; jedes Thema hat eine eigene Seite `/contact/<thema>/` (Themen und Formular-IDs in `src/data/contact.json`) |
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

## Hosting und Veröffentlichung

Die Website wird als statische Website über GitHub Pages im Legacy-Modus veröffentlicht. Das heißt:

- Branch: `main`
- Auslieferung: Root-Ordner `/`
- Build: kein GitHub Actions/Workflow
- Veröffentlichung: ausschließlich durch Pushes auf `main`
- Keine andere Publikationslogik ist aktiv

Die Website lebt daher nicht aus `src/` oder einem Workflow heraus. Die wirklich veröffentlichte Ausgabe besteht aus den generierten HTML-Dateien im Repository-Root (`index.html`, `blog/...`, `legal/...`, `de/...`, usw.).

### Standard-Workflow für jede Veröffentlichung

1. Änderungen im Quellcode im richtigen Branch machen.
2. Falls Inhalte, Templates oder Generatorlogik geändert wurden, build ausführen:

```sh
python3 src/scripts/build.py
```

3. Danach sicherstellen, dass die generierten HTML-Dateien im Root aktualisiert sind und committed werden. Wichtige Regel: Es reicht nicht, nur `src/` zu committen; die tatsächlichen publizierten Seiten liegen im Root.
4. `main` aktualisieren:

```sh
git fetch origin
```

5. Falls der aktuelle Branch nicht `main` ist, auf `main` wechseln bzw. fast-forward mit `origin/main` und anschließend den Branch in `main` pushen. Der Veröffentlichungsweg ist immer direkt auf `main`, nicht über einen Workflow oder einen separaten Deploy-Branch.
6. Pushen auf GitHub:

```sh
git push origin HEAD:main
git push origin HEAD
```

7. Nach dem Push warten, bis GitHub Pages den Build fertiggestellt hat.

### Verifikation nach dem Publish

Nach dem Push muss die Seite live geprüft werden. Das ist der einzige Nachweis der Veröffentlichung:

```sh
gh api repos/0nhub/homepage/pages/builds/latest --jq '.status+" "+.commit[0:7]'
```

Erwartung: der Status muss auf `built <commit>` laufen. Wenn der Status noch `building` ist, warten. Danach live prüfen:

```sh
curl -s "https://sgroi.ga/blog/?x=$RANDOM"
curl -s "https://sgroi.ga/blog/keyboard-shortcuts-the-hidden-superpowers/?x=$RANDOM"
```

Nur so ist die Veröffentlichung als erfolgreich bestätigt.

### Build- und Commit-Regel

Der komplette, verbindliche Ablauf für Content- und Layout-Änderungen ist:

```sh
python3 src/scripts/build.py

git add -A

git commit -m "Rebuild static pages" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
```

Wenn der aktuelle Branch nach `origin/main` noch nicht in `main` liegt, erst fast-forward oder rebase, dann builden und committen, dann auf `main` pushen.

### Absolute Regeln für die Kommunikation

Diese Punkte müssen in allen Gesprächen und Beschreibungen beachtet werden:

- Keine Behauptung wie „es gibt keinen Publish-Weg“ ohne vorherige Prüfung des Repos.
- Keine Bezugnahme auf einen Workflow, wenn das Repo bewusst keinen Workflow hat.
- Die tatsächliche Publikation erfolgt immer durch Push auf `main`.
- Generierte HTML im Root muss bei jeder Veröffentlichung aktuell und committed sein.
- `src/` allein ist nie die Live-Ausgabe.
- Ein lokaler Preview ist lediglich eine Validierung; er ersetzt keine Veröffentlichung.
- Der reale Nachweis der Live-Veröffentlichung ist ein erfolgreiches GitHub Pages Build und ein HTTP-Check auf `https://sgroi.ga` bzw. der Ziel-URL.

### Allgemeine Arbeitsregeln

1. Prüfungen zuerst auf die tatsächliche Repo-Architektur; nicht auf Vermutungen.
2. Lokale Vorschau nur als Test; nicht als Beweis für Live-Publikation.
3. Bei Änderungen an Inhalten, CSS, Blog-Posts oder Seiten immer builden und die generierten Root-Dateien mitcommitten.
4. Publikationsanweisungen immer anhand der realen Hosting-Architektur formulieren.
5. Wenn eine Änderung live sein soll, muss sie auf `main` publiziert werden; nicht nur in einem Feature-Branch.

Die Originaldateien wurden vor der Umstellung zusätzlich unter `/tmp/sgroi-before-restructure/` gesichert; dieses temporäre Verzeichnis ist kein dauerhaftes Backup.
