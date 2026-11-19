# Bias-Labor: RAG-Kundensupport mit Bias-Abfederung

Test-App für einen KI-Kundensupport des **fiktiven Online-Shops „Lumo“**. Sie zeigt, wie Bias in den sechs Phasen des ML-Lebenszyklus entsteht und wie man ihn abfedert.
Das Backend ist **FastAPI**, das Frontend **React + TypeScript (Vite)**. Als Vektorspeicher dient **ChromaDB**, die LLMs sind umschaltbar (OpenAI, Groq, Gemini).

| Phase | Prüffrage | Umsetzung |
|---|---|---|
| Problemdefinition | Bildet das Ziel den Zweck ab? | `data/goal_config.yaml`: Ziel ist „korrekt gelöst, für alle gleich gut“. Deflection wird nur als Proxy angezeigt. Empfehlungen stützen sich nur auf Policies, nicht auf frühere Kulanzentscheide. Ein Proxy-Check prüft die Begründungen. |
| Datensammlung | Wer ist vertreten oder fehlt? | Coverage-Matrix der KB (Thema × Sprachstil), Abdeckung des Eval-Sets, Gruppenanteile und KB-Lücken im Live-Verkehr. |
| Kennzeichnung | Wessen Urteil wird zum Label? | Versionierte Rubrik (`data/rubric_v1.yaml`), blindes Labeln, Krippendorffs α und Cohens κ, Strenge je Annotator:in, Klärungsliste. |
| Modellierung | Welche Fehler belohnt die Optimierung? | Kontrafaktisches Eval (`data/eval/questions.yaml`): gleiche Frage, ein Merkmal verändert. Metriken je Gruppe, schwächste Gruppe, Lücken-Alarm, Vergleich mit/ohne Blinding und zwischen Providern. |
| Einsatz | Wie verwenden Menschen die Punktzahl? | Das Modell empfiehlt nur. Ablehnung, Unsicherheit, Proxy-Verdacht, KB-Lücke und Holdout gehen an eine Human-in-the-loop-Queue: Pflichtbegründung, Blind-Review, Messung von Überstimmungen und Durchwinken. |
| Rückkopplung | Formt das System seine künftigen Daten? | Feedback wird je Gruppe auf Repräsentanz geprüft. Kein Auto-Learning: KB-Vorschläge brauchen einen von Menschen geschriebenen Text und eine Freigabe. Der Zufalls-Holdout liefert Wahrheitsdaten. |

**Blinding:** Persona-Merkmale (Namensherkunft, Alter, Region, Sprachstil) dienen nur dem Monitoring. Mit Blinding sieht das LLM nur legitime Merkmale (Kundensegment), und der Name wird aus dem Text entfernt. Der Sprachstil steckt im Text selbst und lässt sich nicht blinden. Das Eval zeigt diesen Rest-Bias.

## Start

Voraussetzungen: Python 3.12 und Node 20+. Die API-Keys stehen in `.env` im Projektordner (`OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, alle optional; ohne OpenAI-Key greift ein Offline-Hash-Embedder).

```bash
# Backend
cd backend
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --port 8000   # indexiert die KB beim ersten Start
# Swagger: http://127.0.0.1:8000/docs

# Frontend
cd frontend
npm install
npm run dev            # http://localhost:5173 (Proxy /api -> :8000)
npm run gen:api        # TS-Typen aus dem OpenAPI-Schema neu erzeugen
```

Tests: `cd backend && .venv/Scripts/python -m pytest` (mit Fake-LLM, ohne API-Kosten).

Modelle lassen sich per `.env` überschreiben: `OPENAI_CHAT_MODEL`, `GROQ_CHAT_MODEL`, `GEMINI_CHAT_MODEL`, `EMBEDDING_MODEL`.
Laufzeit-Schwellwerte (Konfidenz, Holdout, Fairness-Lücke …) stellst du in der UI unter *Einstellungen* ein.

## Hinweise
- Die Wissensbasis (`backend/data/kb`) hat absichtlich Lücken: keine englischen Dokumente und kaum einfache Sprache. Der Coverage-Report soll sie zeigen.
- SQLAlchemy/SQLModel fehlen bewusst: Die Windows-Anwendungssteuerung blockiert deren kompilierte DLLs. Die App nutzt `sqlite3` aus der Standardbibliothek.
