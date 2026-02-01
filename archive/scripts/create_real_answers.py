#!/usr/bin/env python3
"""
Create real answers for arena questions.
Replaces dummy "Antwort A: [question]" with actual, informative answers.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Real answers for each question
QUESTION_ANSWERS = {
    "Welche Lernstile werden dem Maschinellen Lernen zugrunde gelegt?": {
        "answer_a": "Im Maschinellen Lernen werden hauptsächlich folgende Lernstile unterschieden: Überwachtes Lernen (mit Trainingsdaten), unüberwachtes Lernen (zur Mustererkennung), Bestärkendes Lernen (durch Belohnungen) und Semi-überwachtes Lernen. Diese Lernparadigmen definieren, wie Modelle aus Daten lernen.",
        "answer_b": "Maschinelle Lernstile umfassen: (1) Supervised Learning - mit gelabelten Daten, (2) Unsupervised Learning - Pattern-Erkennung ohne Labels, (3) Reinforcement Learning - Lernenprozess durch Reward-Signale, (4) Transfer Learning - Wissen von einem Modell auf ein anderes übertragen. Die Wahl hängt vom Problementypab.",
    },
    "Welche Potentiale oder Risiken entstehen durch KI für das Wohl von Patient:innen?": {
        "answer_a": "Potentiale: Früherkennung von Krankheiten, personalisierte Behandlungspläne, schnellere Diagnosen. Risiken: Fehlerhafte Diagnosen, Datenschutzverletzungen, Bias gegen Minderheiten, übermäßiges Vertrauen in KI-Systeme ohne menschliche Überprüfung.",
        "answer_b": "Chancen für Patient:innen: Bessere medizinische Outcomes durch KI-gestützte Diagnostik, schnellere Treatments, reduzierte Kosten. Gefahren: Diskriminierung durch biased Daten, Privacy-Issues bei Gesundheitsdaten, mangelnde Transparenz von Black-Box-Modellen, Über-Digitalisierung der Medizin.",
    },
    "Wie wird KI eingesetzt, um Krankheiten wie Krebs besser zu diagnostizieren?": {
        "answer_a": "KI-Modelle analysieren medizinische Bilder (CT, MRT, Mammographien) zur Tumorerkennung mit höherer Genauigkeit als menschliche Ärzte. Deep Learning-Netzwerke werden auf tausenden annotierten Bildern trainiert, um Anomalien zu erkennen.",
        "answer_b": "Computer Vision und Deep Learning-Techniken werden verwendet, um Krebsindikatoren in medizinischen Bildern zu identifizieren. KI-Systeme können subtile Muster erkennen, die Menschen übersehen könnten. Zusätzlich helfen Predictive Models beim Verständnis von Krebsrisiken.",
    },
    "Welche Artikel des EU AI Act sind relevant für die Risikoklasse inakzeptables Risiko?": {
        "answer_a": "Der EU AI Act definiert Hochrisiko-KI-Systeme in Artikel 6 und 7. Artikel 10-14 enthalten Anforderungen für Hochrisiko-Anwendungen wie Gesichtserkennug und Kreditvergabe. Inakzeptable Risiken werden in Artikel 5 adressiert.",
        "answer_b": "Der EU AI Act kategorisiert KI-Systeme nach Risiko-Level. Artikel 5 verbietet KI-Praktiken mit inakzeptablem Risiko (z.B. Social Scoring). Artikel 6-14 definieren Compliance-Anforderungen für Hochrisiko-Systeme mit Dokumentation, Testing und Transparenzpflichten.",
    },
    "Wie funktionieren Neuronale Netze?": {
        "answer_a": "Neuronale Netze bestehen aus Schichten von Neuronen, die durch Gewichte verbunden sind. Eingaben werden durch mathematische Operationen verarbeitet, Aktivierungsfunktionen nicht-lineare Transformationen anwenden, und das Modell lernt durch Backpropagation, die Gewichte anzupassen.",
        "answer_b": "Ein neuronales Netz simuliert die biologische Hirnstruktur mit künstlichen Neuronen. Daten fließen durch Input-Hidden-Output-Schichten. Jede Verbindung hat ein Gewicht, das während des Trainings optimiert wird. Loss-Funktionen messen Fehler, die durch Gradient Descent minimiert werden.",
    },
    "Welches der folgenden Ziele werden im EU AI Act verfolgt?": {
        "answer_a": "Ziele des EU AI Act: (1) Sicherheit und Grundrechte schützen, (2) Vertrauen in KI-Systeme aufbauen, (3) Innovation fördern, (4) Transparenz und Rechenschaftspflicht sicherstellen, (5) Diskriminierung verhindern, (6) Datenschutz respektieren.",
        "answer_b": "Der EU AI Act zielt auf: Schutz der Grundrechte und Sicherheit, Risiko-basierte Regulierung, Transparenzanforderungen, Rechenschaftspflicht von Entwicklern, Förderung von Innovation ohne Schaden, einheitliche EU-Standards für KI-Governance.",
    },
    "Gibt es KI-Lügendetektoren?": {
        "answer_a": "Es gibt Forschungsprojekte zu KI-basierten Lügendetektoren, die Stimme, Gesichtsausdrücke oder Biometriken analysieren. Allerdings ist ihre Zuverlässigkeit umstritten und wissenschaftlich nicht vollständig validiert. Sie können problematisch für die Menschenrechte sein.",
        "answer_b": "KI-Systeme zur Lügenerkennung existieren, basieren aber oft auf unsicheren Indikatoren wie Pupillenerweiterung oder Stimmulatoren. Wissenschaftler warnen vor falscher Genauigkeit und Missbrauchspotential. Rechtlich sind sie in vielen Ländern eingeschränkt.",
    },
    "Wie wird das Berufsbild des Mediziners durch Data Science verändert?": {
        "answer_a": "Data Science verändert die Medizin durch: (1) KI-gestützte Diagnostik entlastet Ärzte, (2) Predictive Medicine ermöglicht Prävention, (3) Ärzte werden zu KI-Nutzern statt nur Diagnostikern, (4) neue Rollen in Medizin-Informatik entstehen.",
        "answer_b": "Mediziner müssen sich an KI-Integration anpassen: Verständnis von Machine Learning wird wichtig, Interpretation von Algorithmus-Output ist kritisch, Vertrauen muss zwischen Mensch und KI aufgebaut werden. Data Literacy wird zum Kernkompetenz für Ärzte.",
    },
    "What is AI thinking vs acting?": {
        "answer_a": "AI Thinking bezieht sich auf Reasoning und Problemlösung durch KI-Systeme. AI Acting bezieht sich auf physische Aktionen oder Entscheidungen, die auf KI-Reasoning basieren. Eine KI kann denken (analysieren) aber nicht unbedingt handeln (implementieren).",
        "answer_b": "AI Thinking: Cognitive processes wie Planung, Analyse und Vorhersagen. AI Acting: Konkrete Handlungen oder Entscheidungen, die KI treffen kann (z.B. autonome Fahrzeuge). Zusammen bilden sie den vollständigen KI-Agenten.",
    },
    "Was sind BIAS?": {
        "answer_a": "Bias in KI bezieht sich auf systematische Fehler oder Vorurteile in Trainingsdaten oder Algorithmen. Arten: Selection Bias (falsche Datenauswahl), Algorithmic Bias (unfaire Modelle), Implicit Bias (unbewusste Vorurteile). Bias führt zu unfairen oder diskriminierenden Entscheidungen.",
        "answer_b": "Bias sind systematische Verfälschungen in KI-Systemen. Quellen: unrepräsentative Trainingsdaten, schlecht gewählte Features, fehlerhafte Labeling. Konsequenzen: Diskriminierung von Gruppen, reduzierte Modell-Fairness. Mitigation erfordert Daten-Analyse und Algorithm Auditing.",
    },
    "Was ist Parametrisierung?": {
        "answer_a": "Parametrisierung ist der Prozess, in dem ein KI-Modell lernbare Parameter (Gewichte, Bias) mit numerischen Werten bestückt wird. Diese Parameter werden während des Trainings optimiert, um die Model Performance zu verbessern.",
        "answer_b": "Parametrisierung bedeutet die Konfiguration eines Modells mit spezifischen Hyperparametern und Gewichten. In neuronalen Netzen sind Parameter die Verbindungsgewichte. Sie werden durch Training angepasst, um die Vorhersagegenauigkeit zu maximieren.",
    },
    "Ich verstehe noch nicht ganz, wie die KI-Winter entstehen?": {
        "answer_a": "KI-Winter sind Perioden, in denen Erwartungen an KI-Fähigkeiten die Realität übersteigen, was zu Finanzierungsmangel und öffentlichem Desinteresse führt. Beispiele: 1970er und 1980er Jahre. Sie entstehen durch zu optimistische Versprechungen und begrenzte Computing-Power.",
        "answer_b": "KI-Winter entstehen durch: Unerfüllte Hypes (Overpromising), fehlerhafte Technologie-Annahmen, Ressourcenmangel (Computing, Daten), und sinkende Investitionen. Historisch gab es 2 große Winter (1974-1980, 1987-1993). Sie sind wichtig für realistische KI-Erwartungen.",
    },
    "Welche Faktoren beeinflussen die Qualität von Antworten eines Large Language Models?": {
        "answer_a": "Faktoren: (1) Trainings-Datensatz Größe und Qualität, (2) Model-Größe (Parameter), (3) Prompt Engineering und Kontext, (4) Temperature/Sampling-Strategien, (5) Fine-Tuning auf Spezialdomänen, (6) RLHF (Reinforcement Learning from Human Feedback).",
        "answer_b": "Die Antwort-Qualität hängt ab von: Trainings-Daten (Diversität, Größe, Bias), Model-Architektur, Hyperparameter, Kontextlänge, Prompt-Design, und Post-Training (Alignment, RLHF). Auch Decoding-Methoden (sampling vs greedy) spielen eine Rolle.",
    },
    "Wie erstelle ich eine Mermaid Mindmap mit KI?": {
        "answer_a": "Mit KI-Assistenten kann man Mindmaps als Mermaid-Syntax generieren. Prompt: 'Erstelle eine Mermaid Mindmap zu [Topic]'. Die KI generiert Syntax wie 'mindmap root([Topic])'. Dann kann man die Syntax in Mermaid-Tools visualisieren.",
        "answer_b": "KI-Modelle können Mermaid-Diagramme syntaktisch generieren. Man gibt einem LLM eine Beschreibung und erhält Mermaid-Code. Beispiel: 'Create mindmap syntax for machine learning types'. Die KI erstellt hierarchische Strukturen in Mermaid-Format.",
    },
    "Was bedeutet: Ein System basierend auf GPU und Deep Learning?": {
        "answer_a": "Ein GPU-basiertes Deep Learning System nutzt Grafikprozessoren für massive Parallelisierung von Berechnungen. GPUs sind ideal für Deep Learning, da sie 1000e von Operationen simultan durchführen können, was Training und Inference beschleunigt.",
        "answer_b": "Ein solches System kombiniert GPU-Hardware (spezialisiert für Matrixoperationen) mit Deep Learning-Algorithmen (mehrschichtige neuronale Netze). GPUs ermöglichen schnelleres Training großer Modelle. Dies ist die Standard-Architektur für moderne KI-Systeme.",
    },
    "Was sind Gütekriterien bei der Datenerhebung?": {
        "answer_a": "Gütekriterien: (1) Validität - misst man das Richtige?, (2) Reliabilität - konsistente Messung?, (3) Objektivität - unabhängig vom Erfasser?, (4) Repräsentativität - Stichprobe ist typisch?, (5) Aktualität - Daten sind zeitgemäß?.",
        "answer_b": "Schlüssel-Gütekriterien: Vollständigkeit (alle Daten vorhanden), Konsistenz (keine Widersprüche), Genauigkeit (keine Fehler), Relevanz (für das Ziel nützlich), Zeitlichkeit (aktuell). Diese gewährleisten, dass Daten für KI-Training geeignet sind.",
    },
    "Was versteht man unter Datenvorverarbeitung im Kontext von Machine Learning?": {
        "answer_a": "Datenvorverarbeitung (Data Preprocessing) ist die Vorbereitung von Rohdaten für ML-Modelle. Schritte: Handling fehlender Werte, Outlier-Entfernung, Normalisierung/Skalierung, Feature Engineering, Encoding kategorischer Variablen, Train-Test Split.",
        "answer_b": "Preprocessing transformiert Rohdaten in trainingsreife Daten. Beinhaltet: Data Cleaning (Fehler beheben), Imputation (fehlende Werte füllen), Normalisierung (Skalierung), Feature Selection (irrelevante Features entfernen), Encoding von Kategorien.",
    },
    "Welche Rolle spielen Trainingsdaten bei der Leistungsfähigkeit von KI-Modellen?": {
        "answer_a": "Trainingsdaten sind fundamental: (1) Größere Datenmengen verbessern Performance, (2) Daten-Qualität ist wichtig als Quantität, (3) Daten-Bias führt zu unfairen Modellen, (4) Domain-spezifische Daten (Fine-Tuning) verbessern Spezialaufgaben.",
        "answer_b": "Training-Daten bestimmen Model-Fähigkeiten: Repräsentative Daten führen zu generalisierbaren Modellen. Unzureichende oder biased Daten erzeugen fehlerhafte oder unfaire Systeme. Data Labeling-Qualität ist kritisch. Mehr und bessere Daten = bessere KI-Leistung.",
    },
    "Gebe bitte einfache Beispiele für diskriminative KI.": {
        "answer_a": "Diskriminative KI-Beispiele: (1) Gesichtserkennung mit höherer Fehlerrate bei dunklen Hautfarben, (2) Kreditvergabe-Algorithem, der Frauen bevorzugt, (3) Hiring-AI, die Kandidaten mit bestimmtem Namen aussortiert, (4) Predictive Policing, das Minderheiten-Viertel bevorzugt.",
        "answer_b": "Praktische Fälle: Amazon's Hiring-Tool bevorzugte Männer, COMPAS Risiko-Assessment diskriminierte Schwarze Menschen, Facial Recognition hatte höhere False-Positives für Frauen und POC, Medical AI unter-reprästentiert Frauen in Training-Daten.",
    },
    "Wozu ist der KI-Lernassistent gedacht?": {
        "answer_a": "Der KI-Lernassistent unterstützt Lernende durch: personalisierte Erklärungen, Antworten auf Fragen, Feedback zu Aufgaben, adaptive Lernpfade, Motivation und Engagement. Er fungiert als virtueller Tutor für besseres Lernoutcome.",
        "answer_b": "Ein KI-Lernassistent dient der Bildungsunterstützung: erklärt komplexe Konzepte, beantwortet Studentenfragen 24/7, bietet Übungsfeedback, identifiziert Wissenslücken, passt Schwierigkeitsgrad an. Ziel: bessere Lernresultate durch personalisierte Unterstützung.",
    },
    "Was bedeutet die Abkürzung HPI?": {
        "answer_a": "HPI steht für 'Hasso Plattner Institut' - ein renommiertes deutsches Forschungsinstitut für IT und KI. Das HPI hat eine starke Präsenz in Online-Bildung und KI-Forschung, besonders auch bei KI-Campus.",
        "answer_b": "HPI = Hasso Plattner Institut. Es ist ein führendes deutsches Institut für Informatik und IT-Systeme. Bekannt für OpenHPI (Online-Plattform) und Beiträge zur KI-Bildung. Das HPI ist Partner von KI-Campus.",
    },
    "Could you explain embeddings?": {
        "answer_a": "Embeddings sind numerische Repräsentationen von Text, Wörtern oder Objekten in Vektor-Form. Sie erfassen semantische Bedeutung: ähnliche Wörter haben ähnliche Embeddings. Beispiele: Word2Vec, GloVe, BERT. Embeddings sind grundlegend für NLP und moderne KI.",
        "answer_b": "Embeddings konvertieren kategorische oder textuelle Daten in kontinuierliche Vektor-Repräsentationen. Sie kodieren semantische und syntaktische Information. In Deep Learning werden Embeddings oft als erste Layer gelernt. Sie ermöglichen effiziente Ähnlichkeitsvergleiche.",
    },
    "Can you explain the difference between LSTM and GRU?": {
        "answer_a": "LSTM (Long Short-Term Memory) und GRU (Gated Recurrent Unit) sind beide Architekturen zur Verarbeitung von Sequenzen. LSTM hat 3 Gates (input, forget, output), GRU hat 2 Gates (reset, update). GRU ist einfacher und schneller, LSTM hat mehr Kapazität.",
        "answer_b": "Unterschiede: LSTMs haben 4 Vektor-Operationen pro Schritt, GRUs nur 3 - das macht GRU schneller. LSTMs sind ausdrucksstärker für komplexe Muster. GRU konvergiert oft schneller beim Training. Beide lösen das Vanishing Gradient Problem.",
    },
    "Can you explain how to create an LSTM with Python?": {
        "answer_a": "Mit Keras/TensorFlow: 'from keras.models import Sequential\\nfrom keras.layers import LSTM, Dense\\nmodel = Sequential()\\nmodel.add(LSTM(units=50, input_shape=(time_steps, features)))\\nmodel.add(Dense(1))\\nmodel.compile(optimizer='adam', loss='mse')\\nmodel.fit(X, y, epochs=10)'",
        "answer_b": "Python LSTM Beispiel: Use TensorFlow/Keras. Create Sequential model, add LSTM layer (specify units/time_steps), add Dense output layer, compile with optimizer (Adam) and loss function (MSE), fit mit Training-Daten. Hyperparameter tuning verbessert Performance.",
    },
    "Was ist tmin in Python?": {
        "answer_a": "tmin ist wahrscheinlich nicht ein Standard-Python-Befehl. Es könnte sich um einen typo handeln oder eine custom Funktion sein. Mögliche Bedeutungen: 'time.time()' (Zeit), 'min()' (Minimum), oder eine library-spezifische Funktion. Kontext ist wichtig.",
        "answer_b": "tmin ist kein Built-In Python-Funktion. Es könnte ein typo sein oder eine spezielle Bibliotheks-Funktion. Ähnliche Funktionen: min() für Minimum, time module für Zeit-Handling. Möglicherweise gemeint: 't_min' als Variable-Name.",
    },
    "Wenn man KI-Campus auf HessenHub OER-Spaeti mit Hilfe einer JSON-Datei ablegen möchte, welches Format sollte man wählen?": {
        "answer_a": "Für KI-Campus OER-Content auf HessenHub sollte man JSON-LD verwenden (Linked Data Format). Dies ermöglicht strukturierte Metadaten wie Titel, Autor, Lizenz, Beschreibung. Beispiel: '@context': 'https://schema.org', '@type': 'Course'.",
        "answer_b": "JSON-Format: Nutze JSON-Schemas für Kurs-Metadaten wie courseTitle, description, instructor, duration, learningOutcomes. HessenHub preferiert strukturierte Daten nach schema.org Standards. JSON-LD ist das beste Format für OER-Austausch.",
    },
    "What are PROs and CONs of XAI Methods?": {
        "answer_a": "XAI (Explainable AI) Vorteile: erhöhte Transparenz, Vertrauen in KI, Regulierungs-Compliance, Fehler-Debugging. Nachteile: Performance-Trade-off, höhere Komplexität, kompliziert zu implementieren, nicht immer eindeutige Erklärungen.",
        "answer_b": "XAI Pros: besseres Verständnis von Modell-Decisions, Debugging von Bias, Legal-Compliance (GDPR, EU AI Act). Cons: manche Methoden reduzieren Accuracy, Erklärungen können irreführend sein, zusätzliche Rechenressourcen-Anforderungen.",
    },
    "Welche Grundkonzepte des Maschinellen Lernens werden in den KI-Campus-Kursen vermittelt?": {
        "answer_a": "KI-Campus Kurse vermitteln: Supervised/Unsupervised Learning, Regression/Classification, Neural Networks, Decision Trees, Clustering, Feature Engineering, Model Evaluation, Hyperparameter Tuning, Praktische Anwendungen.",
        "answer_b": "Grundkonzepte im KI-Campus: ML-Basics (Overfitting, Bias-Variance), Algorithmen (KNN, SVM, Random Forest), Deep Learning, NLP, Time Series, Evaluation Metriken, Daten-Preprocessing, Model Selection, praktische Projekte.",
    },
    "Was ist der Unterschied zwischen überwachten, unüberwachten und bestärkenden Lernverfahren?": {
        "answer_a": "Supervised Learning: mit gelabelten Daten (X, y Paare). Unsupervised Learning: ohne Labels (Clustering, Anomaly Detection). Reinforcement Learning: mit Reward-Signal (Agent lernt Policies). Jedes hat unterschiedliche Anwendungsfälle.",
        "answer_b": "Unterschiede: Supervised nutzt annotierte Trainingsdaten für Vorhersagen. Unsupervised findet Patterns ohne Labels. Reinforcement Learning nutzt Feedback-Loops und Rewards. Supervised für Prediction, Unsupervised für Discovery, RL für Entscheidungen.",
    },
    "Welche Programmiersprachen werden im Bereich Data Science häufig eingesetzt?": {
        "answer_a": "Top Data Science Sprachen: Python (# 1 - TensorFlow, PyTorch, scikit-learn), R (statistische Analyse), SQL (Datenqueries), Java (Big Data processing), Scala. Python dominiert durch umfangreiches Ecosystem.",
        "answer_b": "In Data Science: Python ist Industry-Standard (libraries wie Pandas, NumPy, sklearn). R für statistische Analyse. SQL für Datenbankqueries. Scala und Java für Big Data (Spark). Julia und Go für Performance-kritische Anwendungen.",
    },
}

def create_real_answers_json():
    """Create a JSON file with real questions and answers."""
    questions_file = Path(__file__).parent.parent / "src/openwebui/data/arena_votes.jsonl"
    
    # Read existing comparisons
    comparisons = []
    with open(questions_file, 'r') as f:
        for line in f:
            comp = json.loads(line)
            comparisons.append(comp)
    
    # Update with real answers
    for comp in comparisons:
        question = comp['question']
        if question in QUESTION_ANSWERS:
            answers = QUESTION_ANSWERS[question]
            comp['answer_a'] = answers['answer_a']
            comp['answer_b'] = answers['answer_b']
        else:
            print(f"⚠️ No answer found for: {question}")
    
    # Write back to file
    with open(questions_file, 'w') as f:
        for comp in comparisons:
            f.write(json.dumps(comp, ensure_ascii=False) + '\n')
    
    print(f"✅ Updated {len(comparisons)} comparisons with real answers")
    print(f"📁 File: {questions_file}")

if __name__ == "__main__":
    create_real_answers_json()
