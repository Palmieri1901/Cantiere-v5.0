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
