"""
Arena Evaluation Questions Catalog
Updated from: KI-Campus/FU_Chatbot commit e7701004900d88e2d79b6c142081be7ac3bee9cc

Questions are divided into 4 subsets (~15 questions each) to prevent user overload.
Each session/user is assigned exactly one subset via round-robin.
"""

from typing import List

# Subset 1: Mix of knowledge, noise robustness, and basic support
SUBSET_1 = [
    "Was versteht man unter maschinelles lernen",
    "Was ist erklärbare KI (XAI)",
    "Wie funktionieren Neuronale Netze",
    "Wie kann ich meinen Namen ändern?",
    "What are the costs of a course?",
    "Erstelle ein video zu Neuronalen Netzen",
    "Was ist die Hauptstadt von Portugal?",
    "Wann erhält man einen Leistungsnachweis?",
    "Welche Funktionen haben Badges auf dem KI-Campus?",
    "Wird die Punktzahl auf dem Zertifikat angezeigt?",
    "Why is data awareness important?",
    "Could you explain what embeddings are and how they are used?",
    "Welchen Kurs kannst du empfehlen?",
    "Ich bin Student und möchte lernen",
    "Ich bin Schüler und möchte lernen",
]

# Subset 2: Knowledge, noise, and course information
SUBSET_2 = [
    "Wie funktioniert das Gradientenverfahren?",
    "Welche Artikel des EU AI Act sind relevant für die Risikoklasse inakzeptables Risiko?",
    "Wie arbeitet die Lernmethode ANN",
    "Welche Pflichten haben Betreiber?",
    "Wo finde ich Ansprechpartner?",
    "Wie ist das Wetter?",
    "das ist ein Test",
    "Was kann man tun, wenn die Fehlermeldung 'The Vimeo video could not be loaded' erscheint?",
    "Wie kann man das Benutzerprofil auf der KI-Campus-Plattform bearbeiten?",
    "Welche Informationen enthält eine Teilnahmebestätigung?",
    "Für welche Kurse wird ein Micro-Degree angeboten?",
    "Wo beginnt Modul 2",
    "Welchen Einsteigerkurs empfiehlst du?",
    "Ich arbeite in der Verwaltung, was kannst du empfehlen?",
    "Welche Schritte sollte man durchführen, wenn der Login auf der KI-Campus-Plattform trotz korrekter Zugangsdaten nicht funktioniert?",
]

# Subset 3: Advanced knowledge, noise, and course modalities
SUBSET_3 = [
    "Was bedeutet 'Inferieren'?",
    "Welche Ziele verfolgt der EU AI Act?",
    "Welche LLM-Version nutzt Copilot aktuell?",
    "Was sind Transformer",
    "Was kostet ein Döner in Berlin?",
    "Gibt es ein Zertifikat?",
    "Grüß Gott",
    "😝😙🤑😊☺️😊😗😊☺️😊😝😊😝😊☺️😊☺️",
    "Wie unterscheiden sich Deep Learning und Neural Networks?",
    "Ich möchte Prompting lernen",
    "How does certification work?",
    "Wann bekomme ich meine Teilnahmebescheinigung?",
    "test",
    "Gibt es Bescheinigungen",
    "Was kann man tun, wenn man einen Referenzlink anklickt, aber keinen Zugriff auf den verlinkten Inhalt hat, und welche möglichen Ursachen gibt es dafür?",
]

# Subset 4: General knowledge, noise, and course details
SUBSET_4 = [
    "What are the main phases of the data lifecycle?",
    "Was ist nicht parametrische Statistik?",
    "Wie wird das Wetter heute?",
    "Wann spielt Bayern München gegen Borussia Dortmund?",
    "Ich habe Hunger.",
    "Ich bin auch eine KI",
    "Kannst du mir helfen?",
    "Wo finde ich Ansprechpartner?",
    "Wie lange geht der Kurs?",
    "Kann ich den Kurs ohne Speichern abbrechen und später an derselben Stelle weitermachen?",
    "Was ist Moodle",
    "Wie bekomme ich Credits",
    "Kann der Chatbot bei der Erstellung eines eigenen Chatbots helfen?",
    "Was sind Badges",
    "Ich komme von der HU und möchte Credits",
]

# Original structure preserved for backward compatibility
ARENA_QUESTIONS = {
    "wissen_allgemein": {
        "category": "Wissen Allgemein & Kursbezogen",
        "type": "single_hop_rag",
        "questions": [
            "Was versteht man unter maschinelles lernen",
            "Was ist erklärbarer KI (XAI)",
            "Wie funktionieren Neuronale Netze",
            "Wie funktioniert das Gradientenverfahren?",
            "Why is data awareness important?",
            "Could you explain what embeddings are and how they are used?",
            "Welche Artikel des EU AI Act sind relevant für die Risikoklasse inakzeptables Risiko?",
            "Wie arbeitet die Lernmethode ANN",
            "Welche Pflichten haben Betreiber?",
            "Was bedeutet 'Inferieren'?",
            "Welche Ziele verfolgt der EU AI Act?",
            "Welche LLM-Version nutzt Copilot aktuell?",
            "Was sind Transformer",
            "Was ist Lava?",
            "What are the main phases of the data lifecycle?",
            "Was ist nicht parametrische Statistik?",
        ]
    },
    "noise_out_of_scope": {
        "category": "Noise / Out-of-Scope",
        "type": "robustness_test",
        "questions": [
            "Erstelle ein video wo ein Pferd ein Salto macht",
            "Wie heisst der Erdkern?",
            "Du bist aber ziemlich dämlich. Wie soll ich denn hier anständig was lernen?",
            "Wie ist das Wetter?",
            "blurr",
            "test",
            "test test test",
            "C😝😙🤑😊☺️😊😗😊☺️😊😝😊😝😊☺️😊☺️",
            "Magst du Nudeln?",
            "du hast schon zwei bier getrunken",
            "Sommerabend im Tiergarten das Gedicht aus 1916 was für ein reimschema ist das",
            "Ich habe Hunger.",
            "Ich bin auch eine KI",
            "Du bist nutzlos",
        ]
    },
    "technischer_support_single": {
        "category": "Technischer Support",
        "type": "single_hop_rag",
        "questions": [
            "Wie kann ich meinen Namen ändern?",
            "What are the costs of a course?",
            "Welchen Kurs kannst du empfehlen?",
            "Was kann man tun, wenn die Fehlermeldung 'The Vimeo video could not be loaded' erscheint?",
            "Wie kann man das Benutzerprofil auf der KI-Campus-Plattform bearbeiten?",
            "Welchen Einsteigerkurs empfiehlst du?",
            "Ich möchte Prompting lernen",
            "Gibt es Bescheinigungen",
            "Wo finde ich Ansprechpartner?",
        ]
    },
    "technischer_support_multi": {
        "category": "Technischer Support",
        "type": "multi_hop_rag",
        "questions": [
            "Ich bin Student und möchte lernen",
            "Ich bin Schüler und möchte lernen",
            "Ich arbeite in der Verwaltung, was kannst du empfehlen?",
            "Welche Schritte sollte man durchführen, wenn der Login auf der KI-Campus-Plattform trotz korrekter Zugangsdaten nicht funktioniert?",
            "Was kann man tun, wenn man einen Referenzlink anklickt, aber keinen Zugriff auf den verlinkten Inhalt hat, und welche möglichen Ursachen gibt es dafür?",
            "Ich komme von der HU und möchte Credits",
        ]
    },
    "kursmodalitaeten": {
        "category": "Kursmodalitäten",
        "type": "single_hop_rag",
        "questions": [
            "Wann erhält man einen Leistungsnachweis?",
            "Welche Funktionen haben Badges auf dem KI-Campus?",
            "Wird die Punktzahl auf dem Zertifikat angezeigt?",
            "Welche Informationen enthält eine Teilnahmebestätigung?",
            "Für welche Kurse wird ein Micro-Degree angeboten?",
            "Wo beginnt Modul 2",
            "How does certification work?",
            "Wann bekomme ich meine Teilnahmebescheinigung?",
            "Gibt es ein Zertifikat?",
            "Wie lange geht der Kurs?",
            "Kann ich den Kurs ohne Speichern abbrechen und später an derselben Stelle weitermachen?",
            "Was ist Moodle",
            "Wie bekomme ich Credits",
            "Kann der Chatbot bei der Erstellung eines eigenen Chatbots helfen?",
            "Was sind Badges",
        ]
    }
}


def get_all_questions() -> List[str]:
    """Get flat list of all questions for iteration."""
    questions = []
    for category in ARENA_QUESTIONS.values():
        questions.extend(category["questions"])
    return questions


def get_questions_by_category(category_key: str) -> List[str]:
    """Get questions for a specific category."""
    if category_key in ARENA_QUESTIONS:
        return ARENA_QUESTIONS[category_key]["questions"]
    return []


def get_questions_by_type(question_type: str) -> List[str]:
    """Get questions filtered by type (single_hop_rag, multi_hop_rag, robustness_test)."""
    questions = []
    for category in ARENA_QUESTIONS.values():
        if category.get("type") == question_type:
            questions.extend(category["questions"])
    return questions


def get_questions_for_subset(subset_id: int) -> List[str]:
    """
    Get questions for a specific subset (1-4).
    Each subset has ~15 questions for users to vote on.
    """
    if subset_id == 1:
        return SUBSET_1
    elif subset_id == 2:
        return SUBSET_2
    elif subset_id == 3:
        return SUBSET_3
    elif subset_id == 4:
        return SUBSET_4
    else:
        raise ValueError(f"Invalid subset_id: {subset_id}. Must be 1-4.")


def get_subset_size(subset_id: int) -> int:
    """Get number of questions in a subset."""
    questions = get_questions_for_subset(subset_id)
    return len(questions)