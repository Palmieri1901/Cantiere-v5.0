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

## Backlog (P0 → P2)
### P1 — enhancements
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
