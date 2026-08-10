# PRD — Portomare: Gestione Cantiere Nautico

## Problem Statement (Original, IT)
"Una app di gestione clienti per un cantiere nautico
Nome, cognome, tipo di barca e lunghezza,
Tipo di sosta dentro/fuori,
Se fuori calcolo dei costi della copertura, alaggio e varo, note dei lavori eseguiti, costo antivegetativa, costo manutenzione motore.
Sono circa 200 posti barca"

## User Choices
- Autenticazione: **Nessuna** (accesso libero, richiesta biometrica non applicabile su web)
- Costi: **Tariffe base configurabili + override manuale per cliente**
- Extra: **Export Excel/CSV** + integrazioni future
- Lingua: **Italiano**
- Design: nessuna preferenza → tema Premium Maritime (Deep Ocean navy + Teak orange, Fraunces + Chivo)

## Personas
- **Titolare cantiere / segreteria**: gestisce l'anagrafica dei 200 posti barca, monitora entrate stimate e scadenze
- **Meccanico / responsabile lavori**: aggiorna note lavori eseguiti e scadenze manutenzione

## Core Requirements (static)
- Anagrafica clienti (nome, cognome, tel, email)
- Dati barca (tipo, lunghezza in metri, tipo sosta dentro/fuori, posto barca 1-200)
- Calcolo automatico costi: sosta, copertura, alaggio, varo, antivegetativa, manutenzione motore
- Override manuale per ogni singolo cliente
- Note lavori eseguiti + scadenze antivegetativa e manutenzione motore
- Vista mappa 200 posti barca
- Configurazione tariffe base globali
- Export CSV/Excel

## Implemented (2026-02-18)
- ✅ Backend FastAPI con MongoDB (motor)
  - CRUD `/api/clienti`
  - `/api/tariffe` GET/PUT (con scaglioni motore HP e lunghezza)
  - `/api/calcola-costi` preview costi
  - `/api/stats` KPI dashboard + scadenze prossime 30gg
  - `/api/posti-barca` griglia 200 posti con stato
  - `/api/export/clienti.csv` e `/api/export/clienti.xlsx`
  - Validazioni: posto duplicato, range 1-200, tipo_sosta valido
- ✅ Frontend React con react-router:
  - **Dashboard** — 4 KPI cards, occupancy progress, pie chart, bar chart, scadenze
  - **Clienti** — tabella con ricerca, filtri sosta, export CSV/Excel, PDF preventivo per riga, edit/delete
  - **ClienteForm** — sheet form con auto-calcolo costi live via API, toggle override, storico lavori strutturato, download PDF
  - **Tariffe** — configurazione con scaglioni (alaggio/varo per lunghezza, manodopera motore per HP, ricambi unitari) + simulazione live
  - **Posti Barca** — griglia 200 tile con popover dettagli cliente

## Iteration 2 (2026-02-18)
- ✅ **PDF Preventivo/Fattura** — endpoint `/api/clienti/{id}/preventivo.pdf` con reportlab (tema navy/teak Portomare), include anagrafica, dettaglio costi, scadenze, storico lavori
- ✅ **Storico lavori strutturato** — nuovo model `Lavoro`, CRUD `/api/lavori`, componente `LavoriSection` con dialog crea/modifica/elimina, stati pianificato/in_corso/completato
- ✅ Bottone PDF in ogni riga della lista Clienti + nel form cliente
- ✅ Testing: 17/17 backend, 11/11 frontend passati al 100%

## Iteration 4 (2026-02-19)
- ✅ **Costo olio motore al litro**: `costo_olio_motore` diventa €/L (default 12), moltiplicato per `litri_olio_motore` del cliente
- ✅ **Litri olio motore** aggiunto nella scheda cliente (nuovo campo, default 3L)
- ✅ **Cavalli motore** (HP) evidenziato meglio in griglia 4-col: Cavalli / Litri / N° candele / N° termostati
- ✅ PDF preventivo mostra "Olio: X L" nell'intestazione e la quantità nella riga olio motore

## Iteration 5 (2026-02-19)
- ✅ **Home landing page** (`/`) con logo, nome cantiere, slogan, indirizzo completo, contatti, orari, sito web, P.IVA. Card stats "Attività in corso". CTA Dashboard / Clienti / Impostazioni.
- ✅ **Impostazioni Cantiere** (`/impostazioni`): editor completo con caricamento logo (base64, PNG/JPG/SVG max 2MB, preview live)
- ✅ **Endpoint `/api/cantiere` GET/PUT** con modello Cantiere (12 campi)
- ✅ **PDF preventivo dinamico**: header mostra logo (se caricato) + nome cantiere + riga contatti completa (indirizzo, telefono, email, P.IVA)
- ✅ **Sidebar Layout dinamica**: brand-link → Home, logo/nome caricati da /api/cantiere
- ✅ **Sosta fuori sede** (nuovo tipo_sosta): sostituisce costo sosta con `costo_movimentazione` (€/m) + `costo_taccaggio` (€/m). Nessuna copertura/alaggio/varo.
- ✅ **Lavaggi stagionali**: switch e costi separati per inizio + fine stagione
- ✅ **Maggiorazione scafo sporco**: applicata automaticamente quando antivegetativa disattivata (€/metro)
- ✅ Testing iter5: 47/47 backend, 100% frontend

## Iteration 8 (2026-02-19)
- ✅ **Multi-anno**: ogni cliente e lavoro ora ha campo `anno` (default anno solare corrente)
- ✅ **Endpoint `/api/anni`**: lista anni con conteggio clienti · POST `/api/anni/apri` per creare nuovo anno (con opzione `duplica_da` che copia clienti e ricalcola costi con tariffe correnti) · DELETE `/api/anni/{anno}` per cancellare completamente un anno
- ✅ Tutti i GET filtrabili per anno: `/clienti`, `/stats`, `/posti-barca`, `/report/incassi` accettano `?anno=X`
- ✅ **Vincolo posto barca** ora unico **per anno** (posto #42 nel 2026 e posto #42 nel 2027 sono validi)
- ✅ **YearContext + YearSelector**: dropdown in sidebar con lista anni + conteggio clienti + azioni "Apri nuovo anno" (con conferma e opzione duplica) e "Elimina anno" (con warning). Selezione salvata in localStorage
- ✅ Tutte le pagine (Clienti, Dashboard, Report, PostiBarca) ricaricano dati al cambio anno
- ✅ Testing iter8: 21/21 backend + frontend flows verificati

## Iteration 7 (2026-02-19)
- ✅ **Autenticazione rimossa** su richiesta utente
- Backend `/api/*` routes ora pubbliche (rimosso `Depends(get_current_user)` da api_router). Router `/api/auth/*` e seed admin ancora presenti nel codice ma non utilizzati.
- Frontend: rimossi `ProtectedRoute`, `AuthProvider`, redirect a `/login`, bottoni logout in Home e sidebar. Ripristinato Layout originale.
- App accessibile direttamente senza credenziali.
- ✅ **Endpoint `/api/backup` GET** — esporta clienti, lavori, tariffe, cantiere in JSON scaricabile
- ✅ **Endpoint `/api/restore` POST** — ripristina completamente da JSON, con validazione pydantic e overwrite totale
- ✅ **Export PDF bulk**: nuovo endpoint `/api/export/preventivi.zip` che genera un archivio con un PDF per ogni cliente (filename `{posto}_{cognome}_{nome}.pdf` sanitizzato)
- ✅ **Autenticazione JWT email/password**:
  - Modello `users` in Mongo con bcrypt hash, seed admin automatico da `.env` (ADMIN_EMAIL/ADMIN_PASSWORD)
  - Auth router: `/api/auth/login`, `/api/auth/register`, `/api/auth/logout`, `/api/auth/me`
  - Cookie httpOnly `access_token` + supporto Bearer token
  - Tutti gli endpoint `/api/*` protetti tramite dependency router-level
  - Frontend: `AuthProvider` + `ProtectedRoute` + pagina `/login` + logout in sidebar e in Home
  - Admin default: `admin@portomare.it` / `portomare2026` (aggiorna in Impostazioni consigliato)
- ✅ Testing iter6: 73/73 backend, 7/7 frontend flows

## Iter9 (2026-02-20) — 4 richieste utente
- ✅ **PDF Report pagamenti stampabile** — nuovo endpoint `GET /api/report/pagamenti.pdf?anno=YYYY&stato=tutti|pagati|non_pagati`. Tabella con Posto, Cliente, Barca, Totale, Stato (verde/rosso), data pagamento. Header con logo/nome cantiere, riepilogo (totali pagati/non pagati), totale finale filtrato. Ordina per cognome.
- ✅ **Filtro Report per stato pagamento** — dropdown in `/report` (data-testid `select-filtro-stato`) con opzioni Tutti/Pagati/Non pagati. Filtra la tabella client-side e passa `stato` al link PDF. Contatore clienti filtrati accanto al dropdown.
- ✅ **Ricambi motore separati 1°/2° motore**:
  - Nuovo campo `girante_2_attivo` in `Cliente`/`ClienteCreate` (Optional[bool]=None per evitare bug reset).
  - Nuovi campi `costo_manodopera_motore_2` e `costo_ricambi_motore_2_totale` esposti dal calcolo.
  - `calcola_costi` restituisce `ricambi_dettaglio` e `ricambi_2_dettaglio` distinti.
  - PDF preventivo con **due tabelle motore separate** ("1° Motore — X HP" e "2° Motore — X HP"), ognuna con proprio subtotale header.
  - Form cliente mostra **due breakdown separati** in UI + toggle "Girante 2° motore" (data-testid `switch-girante-2`).
- ✅ **Backup accessibile in Home** — nuova card in `/` con bottoni "Salva backup" (data-testid `btn-home-backup-download`) e "Recupera backup" (data-testid `btn-home-restore-open`) + dialog di conferma ripristino. Bottoni Impostazioni conservati.

## Iter9 Testing
- ✅ Backend: 8/8 pytest cases in `/app/backend/tests/test_iter9_pdf_and_secondo_motore.py` (report PDF, calcola-costi motore 2, POST/GET cliente, PUT regression pagato+girante_2_attivo preserved, preventivo PDF con motore 2)
- ✅ Frontend self-test: Home backup buttons, Report filter+PDF href params, ClienteForm secondo motore + girante-2 toggle + entrambi i breakdown (subtotali 657€ + 657€ visibili)

## Iter10 (2026-02-20) — Ordine alfabetico + Lavorazioni extra
- ✅ **Ordinamento alfabetico case-insensitive per cognome** in tutti gli endpoint che restituiscono liste clienti: `GET /api/clienti`, `report_pagamenti`, `report_pagamenti.pdf`. Ordine: cognome asc, poi nome asc, ignorando maiuscole/spazi iniziali.
- ✅ **Lavorazioni extra per cliente** (max 20):
  - Nuovo campo `lavorazioni_extra: List[dict]` su `Cliente` (default []) e `Optional[List[dict]] = None` su `ClienteCreate` (per preservare in PUT parziale).
  - Helper backend `_sanitize_lavorazioni_extra`: cap a 20 (→ 400 se superato), normalizza a `{descrizione: str, prezzo: float}`, filtra righe con desc vuota E prezzo 0.
  - Helper `_totale_extra(doc)` riutilizzato in `/api/stats`, `/api/report/incassi` (nuova categoria "lavorazioni_extra"), `/api/report/pagamenti`, `/api/report/pagamenti.pdf`, PDF preventivo.
  - PDF preventivo: nuova sezione **"LAVORAZIONI EXTRA"** con tabella descrizione + prezzo + riga totale, inclusa nel totale principale ("Lavorazioni extra" come voce aggregata).
  - Frontend `ClienteForm.jsx`: sezione dedicata con `+ Aggiungi voce` (max 20), input descrizione + prezzo, pulsante X per rimozione, subtotale extra, contatore "X / 20 voci". Toast se limite raggiunto. Sommato nel "Totale annuale stimato".
  - Frontend `Clienti.jsx`: funzione totale include lavorazioni_extra.
  - Frontend `Report.jsx`: aggiunta categoria "Lavorazioni extra" con colore dedicato (#5A7A9A).

## Iter10 Testing
- ✅ Backend: 10/10 pytest cases in `/app/backend/tests/test_iter10_alpha_and_extra.py`
- ✅ Frontend self-test: ordine alfabetico visibile (Bianchi→Catra→Figo→Rossi→Sandra→Verdi), sezione Lavorazioni extra funzionante (subtotale 730€, totale annuale 2427€), rimozione voce OK

## Iter11 (2026-02-20) — Manodopera motore a 4 fasce
- ✅ Tariffe: aggiunta nuova fascia **2-15 HP** (default 90 €) accanto alle esistenti 16-40 / 41-150 / oltre 150 HP.
  - Backend: nuovo campo `motore_labor_2_15hp` in `Tariffe`/`TariffeUpdate`, logica `calcola_motore_labor` estesa a 4 scaglioni.
  - Frontend: pagina Tariffe con nuova riga "Da 2 a 15 HP", label aggiornati "Da 16 a 40 HP" / "Da 41 a 150 HP" / "Oltre 150 HP". Simulazione preview aggiornata. Hint fasce in ClienteForm aggiornato.
  - Verificato: HP=10 → €90 · HP=30 → €180 · HP=100 → €320 · HP=300 → €550. PUT del solo `motore_labor_2_15hp` non resetta le altre tariffe.

## Iter12 (2026-02-20) — Assegnazione posto barca automatica
- ✅ Nuovo endpoint `GET /api/posti-barca/next?anno=X&escludi_cliente_id=Y` che ritorna il primo posto libero (1-200) per l'anno indicato, escludendo opzionalmente il posto occupato dallo stesso cliente (utile in modifica).
- ✅ Frontend `ClienteForm.jsx`: pulsante ⚡ (Zap icon) accanto al campo "Posto barca" con `data-testid="btn-posto-auto"`. Click → chiama endpoint, riempie il campo e mostra toast con posto assegnato + posti liberi rimasti.

## Iter13 (2026-02-20) — Antivegetativa e Scafo sporco spunte indipendenti
- ✅ Prima: `antivegetativa_attiva=false` implicava automaticamente maggiorazione scafo sporco. Ora sono 2 spunte separate e indipendenti (4 combinazioni possibili).
- ✅ Backend: nuovo campo `scafo_sporco_attivo: bool = False` su `Cliente`, `Optional[bool] = None` su `ClienteCreate`. Signatura `calcola_costi` aggiornata (17° parametro). Endpoint preview `/api/calcola-costi`, POST/PUT `/api/clienti`, duplicazione anno tutti aggiornati.
- ✅ **Migrazione automatica** all'avvio: clienti esistenti con `costo_scafo_sporco > 0` ricevono `scafo_sporco_attivo=True`, tutti gli altri `False`. Idempotente (basata su `$exists`).
- ✅ Frontend `ClienteForm.jsx`: nuovo toggle "Scafo sporco" (data-testid `switch-scafo-sporco`) accanto ad "Antivegetativa". Rimosso il warning giallo obsoleto. Aggiunto info-testo quando entrambi sono OFF. Preview costi include il nuovo parametro.
- ✅ Test 4 combinazioni backend:
  - OFF/OFF → antivegetativa=0, scafo=0
  - ON/OFF → antivegetativa=200, scafo=0
  - ON/ON → antivegetativa=200, scafo=120
  - OFF/ON → antivegetativa=0, scafo=120
- ✅ Migrazione verificata: Bianchi (scafo 90€) e Semp (scafo 75€) preservati con scafo=True; altri 8 clienti con antivegetativa attiva → scafo=False.

## Iter14 (2026-02-20) — Copertura come spunta indipendente
- ✅ Prima: `costo_copertura` era applicato automaticamente per `tipo_sosta="fuori"`. Ora è **una spunta indipendente** (`copertura_attiva`) applicabile su qualsiasi tipo di sosta.
- ✅ Backend: nuovo campo `copertura_attiva: bool = False` (`Optional[bool]=None` in Update). Signature `calcola_costi` 18° parametro. Preview/POST/PUT/duplicazione anno aggiornati.
- ✅ **Migrazione iter14 all'avvio**: clienti con `costo_copertura > 0` ricevono `copertura_attiva=True` (rtr e Verdi preservati con costo 270€ e 360€), altri `False`. Idempotente.
- ✅ Frontend `ClienteForm.jsx`: nuovo toggle "Copertura" (data-testid `switch-copertura`) accanto ad Antivegetativa e Scafo sporco.
- ✅ **Bug fix** collaterale iter13: aggiunti `f.scafo_sporco_attivo` e `f.copertura_attiva` al vettore delle deps di `useEffect` per il ricalcolo preview (mancavano — il toggle non triggerava la refetch).
- ✅ Test 4 casi backend + frontend: dentro+COP-ON=2407€ / dentro+COP-OFF=2207€ (diff 200€), aggiungendo scafo=+120€ → 2527€. API network capture conferma le call.

## Iter16 (2026-02-20) — Copertura bloccata su sosta al coperto
- ✅ Frontend `ClienteForm.jsx`: quando `tipo_sosta === "dentro"` la spunta **Copertura** è disabilitata (opacità 50%, descrizione dinamica "Non applicabile con sosta al coperto") e forzata a `false` tramite `useEffect`.
- ✅ Component `ToggleRow` esteso con prop `disabled`.
- ✅ Test frontend: default (dentro) → disabled=True. Passa a "A terra (fuori)" → abilitato, click ON → totale 3.512€. Ritorno "Al coperto" → disabled=True, totale torna a 2.392€ (copertura esclusa).

## Iter15 (2026-02-20) — Olio piede a litri (come olio motore)
- ✅ Prima `costo_olio_piede` era un costo fisso (25 €). Ora la tariffa è **per litro** e il costo è moltiplicato per la quantità.
- ✅ Backend: nuovi campi `litri_olio_piede: float = 1.0` (default 1L per compat) e `litri_olio_piede_2: float = 1.0` su `Cliente`, `Optional[float]=None` su `ClienteCreate`. Signature `calcola_ricambi` e `calcola_costi` aggiornate. Preview/POST/PUT/duplicazione anno passano i nuovi parametri.
- ✅ PDF preventivo: righe "Olio piede" ora mostrano "X L" e importo = X × tariffa.
- ✅ Frontend: nuovo campo "Litri olio piede" nel form (1° motore) e "Lt olio piede 2°" nel blocco 2° motore. Griglia motore passata da 4 a 5 colonne su desktop. Breakdown dettaglio mostra "(XL)".
- ✅ Tariffe: label aggiornata "Olio piede — Costo per litro".
- ✅ Test: 1L → olio_piede=25€, 3L → 75€ (+50€ nel totale), 0.5L → 12.5€. Toggle re-calcolo funzionante grazie a `litri_olio_piede` nelle deps `useEffect`.
## Iter29 (2026-02-20) — Sosta temporanea = sempre su piazzale
- ✅ Migrazione automatica all'avvio: clienti esistenti con `tipo_sosta="temporanea"` ricevono `alaggio_varo_attivo=True` (visto che sono sempre su piazzale).
- ✅ Frontend `ClienteForm.jsx`: quando l'utente seleziona `tipo_sosta="temporanea"`, `alaggio_varo_attivo` viene attivato automaticamente. Testo informativo sotto il campo giorni: "Sosta temporanea = sempre su piazzale (fuori). Tariffa: € / giorno / metro."
- ✅ Lista clienti `Clienti.jsx`: il badge per temporanea ora mostra "Piazzale (temp.)" per riflettere la natura outdoor.

## Iter28 (2026-02-20) — Filtro Pagati/Non pagati e riepilogo incassi
- ✅ **3 card KPI cliccabili** sopra la lista: "Tutti", "Da incassare" (rosso, con totale € e conteggio non pagati), "Incassato" (verde, con totale € e conteggio pagati). Click → filtra la lista.
- ✅ **Dropdown filtro "Pagamento"** (data-testid `filter-pagamento`) affianco al filtro tipo sosta: Tutti / Solo non pagati / Solo pagati.
- ✅ **Nuova colonna "Pagamento"** nella tabella con badge verde "Pagato" o outline rosso "Non pagato".
- ✅ **Toggle rapido pagato/non pagato** (data-testid `btn-toggle-pagato-{id}`) tra le azioni riga: icona check verde se non pagato → segna come pagato (data odierna); icona X rossa se pagato → segna come non pagato.
- ✅ Test PUT diretto backend conferma il flag `pagato` e `data_pagamento` vengono aggiornati.

## Iter27 (2026-02-20) — Sosta temporanea: tariffa × giorni × metri
- ✅ `calcola_costi`: per `tipo_sosta="temporanea"` il costo è ora `lunghezza × giorni × sosta_temporanea_giornaliera` (prima solo `giorni × tariffa`).
- ✅ Aggiornati label pagina Tariffe e PDF Listino: "€ / giorno / metro".
- ✅ Test: L=7 × 10 gg × 25€ = 1.750€. L=5 × 5 gg × 25€ = 625€ (con tariffa base 25).

## Iter26 (2026-02-20) — Home: nuova collocazione e aspetto dei tasti
- ✅ Hero snellito: 3 sole azioni principali ("Vai al gestionale" primario con shadow, "Gestione clienti" outline con icona Anchor, "Info cantiere" ghost).
- ✅ Nuova sezione **"Azioni rapide"** con 3 card icona+titolo+sottotitolo per: Preventivo veloce (card primary evidenziata), Listino prezzi PDF, Excel commercialista. Ogni card con hover lift, ombra e freccia animata.
- ✅ Nuovo componente `QuickActionCard` con supporto onClick e href (download/newTab).

## Iter25 (2026-02-20) — Dettaglio cliente in-app (senza scaricare PDF)
- ✅ Nuovo componente `/app/frontend/src/pages/ClienteDettaglio.jsx`: dialog che mostra il conteggio completo di ogni cliente direttamente in pagina.
- ✅ Sezioni: Sosta & trattamenti · Alaggio & Varo (con destinazione e × N mov.) · Manutenzione motore (dettaglio 1°+2°) · Lavorazioni extra riga per riga · **TOTALE ANNUALE** grande.
- ✅ Info sintesi in alto: barca, sosta, posto, stato pagamento.
- ✅ Nuova icona "occhio" nella lista clienti (`btn-dettaglio-{id}`) apre il dialog. Pulsante "Scarica preventivo PDF" all'interno del dialog per continuità.
- ✅ Nasconde automaticamente le voci a 0 € per una lettura pulita.
- 🐛 **BUGFIX**: il componente `<ClienteDettaglio>` era importato ma non veniva renderizzato nel JSX di `Clienti.jsx` → l'icona occhio non apriva nulla. Aggiunto rendering del componente. Testing_agent iter11: 100% PASS su tutti gli scenari (apertura dialog, contenuto, chiusura Chiudi/ESC/click-esterno, PDF link, totale coerente con lista).

## Iter24 (2026-02-20) — Moltiplicatore movimenti alaggio+varo
- ✅ Backend: nuovo campo `numero_movimenti: int = 1` su `Cliente` (Optional in `ClienteCreate`). `calcola_costi` accetta il parametro e moltiplica `costo_alaggio` e `costo_varo` per il numero di movimenti richiesti (solo con destinazione="marina_di_campo"; per "altra" resta manuale).
- ✅ Endpoint `/api/calcola-costi` accetta `numero_movimenti`. Test: L=8, 3 movimenti → 300€/300€ (100€ forfait × 3).
- ✅ POST/PUT clienti, preventivo_pdf_inline, duplicazione anno e ricalcola-anno passano il nuovo parametro.
- ✅ PDF preventivo: voci "Alaggio × N mov." e "Varo × N mov." (mostrate solo se N>1).
- ✅ Excel export: nuova colonna "N° movimenti".
- ✅ Frontend `ClienteForm.jsx`: nel blocco "Destinazione alaggio / varo" (visibile solo se toggle ON) c'è un input "Numero movimenti (alaggio + varo)" con placeholder e testo esplicativo.

## Iter23 (2026-02-20) — Alaggio/Varo oltre 5 m come forfait
- ✅ Backend `calcola_alaggio` e `calcola_varo`: la tariffa `alaggio_oltre_5m_per_metro` (e la corrispondente per il varo) è ora trattata come **forfait fisso** per barche > 5 m (prima veniva moltiplicata per la lunghezza). Nome del campo mantenuto per compatibilità DB.
- ✅ PDF Listino e pagina Tariffe: descrizione aggiornata a "Forfait per barche > 5 m".
- ✅ Simulazione anteprima Tariffe usa il valore fisso.
- ✅ Test: L=8 → tariffa forfait "oltre 5m" fissa (non 8× moltiplicato). L=4 → tariffa forfait "fino a 5m".

## Iter22 (2026-02-20) — Ricalcolo automatico all'aggiornamento tariffe
- ✅ Backend: nuovo endpoint `POST /api/tariffe/ricalcola?anno=X` che ricalcola i costi di tutti i clienti dell'anno indicato usando le tariffe correnti. Rispetta `override_costi` (non tocca chi ha costi manuali globali) e destinazione="altra" per alaggio/varo (preserva valori manuali di destinazioni diverse).
- ✅ Frontend `Tariffe.jsx`: salvando le tariffe viene automaticamente chiamato l'endpoint con l'anno in corso (`useYear` context). Toast informa "Tariffe aggiornate · N/M clienti YYYY ricalcolati".

## Iter21 (2026-02-20) — Alaggio/Varo modificabili con destinazione "Altra"
- ✅ Frontend `ClienteForm.jsx`: quando `alaggio_varo_attivo=true` e destinazione="altra" i campi Alaggio/Varo mostrano la **tariffa Marina di Campo come punto di partenza** (pre-fill automatico se valore=0). L'utente può poi modificarli liberamente in base alla nuova destinazione.
- ✅ Preserva i valori manuali: cambi di lunghezza/motore non azzerano più i costi alaggio/varo digitati manualmente.
- ✅ Testo di aiuto aggiornato: "Modifica i costi qui sotto se il movimento verso questa destinazione ha un prezzo diverso dalla tariffa di Marina di Campo."

## Iter20 (2026-02-20) — Spunta indipendente "Alaggio e varo"
- ✅ Nuovo campo `alaggio_varo_attivo: bool = False` su `Cliente` (Optional in `ClienteCreate`).
- ✅ `calcola_costi`: quando `alaggio_varo_attivo=True` i costi alaggio/varo vengono **sempre calcolati** indipendentemente dal tipo di sosta (dentro/fuori/fuori_sede/temporanea). Se destinazione="altra" → costi manuali.
- ✅ Endpoint `/api/calcola-costi` accetta `alaggio_varo_attivo`. Verificato: dentro+7m+attivo=marina → 700€/700€. dentro+attivo=false → 0€. attivo+altra → 0€ (manuale).
- ✅ create/update cliente, preventivo_pdf_inline e duplicazione anno passano il nuovo parametro.
- ✅ **Migrazione iter20** all'avvio: clienti con `tipo_sosta="fuori"` esistenti ricevono `alaggio_varo_attivo=True` (preserva comportamento pre-esistente). Idempotente.
- ✅ Frontend `ClienteForm.jsx`: nuovo toggle "Alaggio e varo" (`switch-alaggio-varo`). Blocco destinazione + costi alaggio/varo ora visibile per **qualsiasi tipo di sosta** quando il toggle è attivo. Deps `useEffect` aggiornate.
- ✅ Test CRUD: POST cliente sosta="dentro"+alaggio_attivo=true → costo_alaggio/varo 600€ calcolati. PDF preventivo contiene "Alaggio" e "Varo" ✅.

## Iter19 (2026-02-20) — Export Excel completo per commercialista
- ✅ Backend `/api/export/clienti.xlsx?anno=X`: rigenerato da zero. 33 colonne human-readable in italiano (Anno, Posto, Cognome, Nome, CF, Indirizzo, Contatti, Barca, Lunghezza, Tipo sosta, Destinazione alaggio, tutti i costi separati con "€", Lavorazioni extra €, TOTALE €, Pagato, Scadenze, Note).
- ✅ Formattazione openpyxl: header navy + testo bianco, riga TOTALI arancio con formule `=SUM()` sulle colonne valuta, formato `#,##0.00 "€"`, larghezze personalizzate, freeze panes A2. Filtro per anno con sheet name "Clienti YYYY".
- ✅ Frontend `Clienti.jsx`: bottone Excel passa `?anno=` corrente.
- ✅ Frontend `Home.jsx`: nuovo CTA "Excel clienti (commercialista)" accanto a Listino prezzi.
- ✅ Test: HTTP 200, file .xlsx 7.4KB, riga TOTALI in fondo con formule SUM.

## Iter18 (2026-02-20) — Lavaggi stagionali al metro lineare
- ✅ Backend: `costo_lavaggio_inizio_stagione` e `costo_lavaggio_fine_stagione` ora sono **tariffe al metro** e vengono moltiplicate per la lunghezza barca in `calcola_costi`.
- ✅ PDF Listino: gruppo "Copertura & trattamenti scafo" mostra "€ / metro" per i lavaggi (prima "forfait").
- ✅ Frontend Tariffe: descrizione dei lavaggi aggiornata a "€ / metro".
- ✅ Test API: L=8 con tariffa 80 → 640€ · L=5 → 400€.

## Iter17 (2026-02-20) — Destinazione alaggio/varo (Marina di Campo vs Altra)
- ✅ Nuovi campi `destinazione_alaggio_varo: str = "marina_di_campo"` e `destinazione_altra_nome: str = ""` su `Cliente` (Optional in `ClienteCreate`).
- ✅ `calcola_costi` estesa: se `destinazione_alaggio_varo == "altra"` e `tipo_sosta == "fuori"` → costo_alaggio/varo restituiti a 0 (l'utente li compila manualmente).
- ✅ Endpoint `/api/calcola-costi` accetta il nuovo parametro. Verificato: Marina + 6m → 600€/600€. Altra + 6m → 0€/0€.
- ✅ `create_cliente`/`update_cliente`/`preventivo_pdf_inline`: quando destinazione="altra", i costi alaggio/varo dell'utente sono sempre preservati (bypass di `override_costi`).
- ✅ PDF preventivo: le voci "Alaggio" e "Varo" mostrano il nome destinazione tra parentesi se destinazione="altra" (es. "Alaggio (Portoferraio)").
- ✅ Frontend `ClienteForm.jsx`: nuovo blocco "Destinazione alaggio / varo" (visibile solo per sosta="fuori") con Select 2 opzioni (Marina di Campo / Altra destinazione) + input testo "Nome destinazione" quando "Altra". I campi Alaggio/Varo diventano editabili senza bisogno di override quando destinazione="altra".
- ✅ Test CRUD backend: POST altra+Portoferraio→350€ preservato · PUT switch a marina_di_campo → auto-ricalcolo 750€ per 7.5m ✅

### P1 — enhancements (aggiornato)
- [ ] Calendario scadenze completo con view mensile (shadcn Calendar)
- [ ] PDF export bello (fattura preventivo per cliente)
- [ ] Sistema promemoria email/SMS per scadenze (integrazione Resend/Twilio)
- [ ] Upload foto barca / documenti (object storage)
- [ ] Storico lavori strutturato (invece di note libere): data, tipo, costo, materiali

### P2 — future
- [ ] Multi-utente con ruoli (segreteria vs meccanico)
- [ ] Report annuale con grafici entrate mensili
- [ ] Autenticazione biometrica via WebAuthn
- [ ] Assegnazione automatica posto barca in base a lunghezza
- [ ] Integrazione WhatsApp Business per comunicazioni clienti
