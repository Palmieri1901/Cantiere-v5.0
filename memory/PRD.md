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

## Iteration 3 (2026-02-19)
- ✅ **Tariffe a scaglioni**: alaggio/varo forfait ≤5m vs oltre 5m per metro
- ✅ **Manodopera motore per potenza HP**: ≤40 HP · 40-150 HP · >150 HP
- ✅ **Ricambi motore configurabili**: girante, olio motore, filtro olio, candela (× n° candele), termostato (× n° termostati), olio piede, anodi interni, anodi esterni, ingrassaggio
- ✅ **Interruttori nella scheda cliente**: `antivegetativa_attiva` e `girante_attivo` (default ON), disattivabili per singolo cliente
- ✅ **Rename UI "Sosta al coperto"**: label più chiaro per posto barca dentro (valore DB `dentro` conservato)
- ✅ Testing iter4: 31/31 backend, 100% frontend


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
