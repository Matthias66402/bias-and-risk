export type PhaseKey = "problem" | "data" | "labeling" | "model" | "deployment" | "feedback";

export const PHASES: { key: PhaseKey; title: string; question: string; example: string; mitigation: string }[] = [
  {
    key: "problem",
    title: "Problemdefinition",
    question: "Bildet das Ziel den eigentlichen Zweck ab?",
    example: "Frühere Einstellungen gelten als ideale künftige Auswahl.",
    mitigation:
      "Ziel ist „korrekt gelöst – für alle gleich gut“, nicht „schnell abgeschlossen“. Empfehlungen stützen sich nur auf Policy-Dokumente, nie auf frühere Kulanzentscheide. Ein Proxy-Check prüft, ob Begründungen Alter, Herkunft o. Ä. nennen.",
  },
  {
    key: "data",
    title: "Datensammlung",
    question: "Wer ist vertreten oder fehlt?",
    example: "Spracherkennung enthält wenige regionale Akzente.",
    mitigation:
      "Coverage-Matrix der Wissensbasis je Thema × Sprachstil, Abdeckung des Eval-Sets und Repräsentanz der Gruppen im Live-Verkehr. Schlechte Retrieval-Treffer werden pro Gruppe ausgewertet.",
  },
  {
    key: "labeling",
    title: "Kennzeichnung",
    question: "Wessen Urteil wird zum Label?",
    example: "Personen wenden eine unklare Regel verschieden an.",
    mitigation:
      "Versionierte Rubrik mit beobachtbaren Stufen, blindes Labeln ohne Persona, mehrere Annotator:innen, Übereinstimmung (Krippendorffs α, Cohens κ) und eine Klärungsliste für strittige Fälle.",
  },
  {
    key: "model",
    title: "Modellierung",
    question: "Welche Fehler belohnt die Optimierung?",
    example: "Gesamtgenauigkeit verbirgt eine schwächere Gruppe.",
    mitigation:
      "Kontrafaktisches Eval: gleiche Frage, nur ein Merkmal verändert. Metriken pro Gruppe, schwächste Gruppe und Lücke statt nur Gesamtwert. Vergleich mit/ohne Blinding und zwischen Providern.",
  },
  {
    key: "deployment",
    title: "Einsatz",
    question: "Wie verwenden Menschen die Punktzahl?",
    example: "Aus einer Empfehlung wird automatische Ablehnung.",
    mitigation:
      "Das Modell empfiehlt nur. Ablehnungen, Unsicheres und Proxy-Verdacht gehen immer an Menschen. Pflichtbegründung, Blind-Review und Messung von Durchwinken (Automation Bias).",
  },
  {
    key: "feedback",
    title: "Rückkopplung",
    question: "Formt das System seine künftigen Daten?",
    example: "Nur ausgewählte Personen erzeugen neue Erfolgsdaten.",
    mitigation:
      "Feedback wird pro Gruppe auf Repräsentanz geprüft. Kein automatisches Lernen: Wissenslücken werden zu Vorschlägen, die Menschen schreiben und freigeben. Ein Zufalls-Holdout liefert Wahrheitsdaten auch für sonst automatisch erledigte Fälle.",
  },
];
