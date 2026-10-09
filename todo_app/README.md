#  To-Do List Manager — Projet Python IA-2

## Description

Application de gestion de tâches (**To-Do List**) avec interface graphique Tkinter.  
Elle charge, crée, modifie et supprime des tâches depuis un fichier **JSON**, valide toutes les saisies, exporte des rapports texte, et gère robustement les erreurs de fichier.

---

## Fonctionnalités

-  **CRUD complet** : Créer, Lire, Modifier, Supprimer des tâches
-  **Recherche** textuelle en temps réel (insensible à la casse)
- **Filtres** : par priorité (basse/moyenne/haute), par statut, urgentes, en retard
- **Statistiques** en temps réel dans le panneau latéral
- **Sauvegarde automatique** après chaque opération CRUD
- **Export rapport** texte dans `output/rapport.txt`
- **Validation stricte** des saisies avec messages d'erreur explicites
- **Gestion d'erreurs** : `FileNotFoundError`, `JSONDecodeError`, `ValueError`, encodage UTF-8

---

## Structure du projet

```
todo_app/
├── README.md               # Ce fichier
├── requirements.txt        # Dépendances Python
├── main.py                 # Point d'entrée
├── src/
│   ├── app.py              # Interface graphique (Tkinter)
│   └── core/
│       ├── models.py       # Classes métiers (Tache, Priorite, Statut)
│       ├── storage.py      # Persistance JSON (TaskStorage)
│       └── logic.py        # Contrôleur (TaskController)
├── data/
│   └── tasks.json          # Fichier de données (créé automatiquement)
├── output/
│   └── rapport.txt         # Rapport exporté
├── tests/
│   └── test_todo.py        # 34 tests unitaires
└── reports/                # Diagrammes UML + rapports PDF
    ├── uml_cas_utilisation.png
    ├── uml_classes.png
    └── uml_sequence.png
```

---

## Installation

### Prérequis
- Python 3.10 ou supérieur
- `pip` à jour

### Étapes

```bash
# 1. Extraire l'archive et se placer dans le dossier
cd todo_app

# 2. (Recommandé) Créer un environnement virtuel
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate.bat      # Windows

# 3. Installer les dépendances
pip install -r requirements.txt
```

> **Note** : `customtkinter` est listé dans requirements.txt mais l'application  
> fonctionne aussi avec Tkinter standard (inclus dans Python par défaut).

---

## Utilisation

```bash
python main.py
```

L'application démarre immédiatement. Si le fichier `data/tasks.json` est absent,  
l'application démarre à vide et crée le fichier au premier enregistrement.

### Interface

| Élément | Description |
|---------|-------------|
|  Barre de recherche | Filtrage en temps réel par titre |
| Panneau gauche | Filtres (priorité, statut, urgentes, retard) + statistiques |
| Tableau central | Liste des tâches avec tri par colonne |
|  Ajouter | Ouvre le formulaire de création (Ctrl+N) |
|  Modifier | Édite la tâche sélectionnée (double-clic aussi) |
| Supprimer | Supprime après confirmation (Suppr) |
|  Exporter rapport | Génère `output/rapport.txt` |

### Codes couleur du tableau

| Couleur | Signification |
|---------|---------------|
| Rouge sombre | Tâche **en retard** (non terminée, date dépassée) |
| Jaune sombre | Tâche **urgente** (priorité haute) |
| Vert sombre | Tâche **terminée** |
| Défaut | Tâche normale |

---

## Format des données (`data/tasks.json`)

```json
[
  {
    "id_tache": 1,
    "titre": "Exemple de tâche",
    "priorite": "haute",
    "date_limite": "2026-04-20",
    "statut": "à faire"
  }
]
```

| Champ | Type | Valeurs acceptées |
|-------|------|-------------------|
| `id_tache` | entier | auto-incrémenté |
| `titre` | chaîne | 1–120 caractères |
| `priorite` | chaîne | `basse`, `moyenne`, `haute` |
| `date_limite` | date | format `YYYY-MM-DD` |
| `statut` | chaîne | `à faire`, `en cours`, `terminée` |

---

## Lancer les tests

```bash
python -m pytest tests/ -v
# Résultat attendu : 34 passed
```

---

## Gestion des erreurs

| Erreur | Comportement |
|--------|--------------|
| Fichier `tasks.json` absent | Démarrage à vide, fichier créé au 1er enregistrement |
| JSON corrompu | Message d'erreur clair + boîte de dialogue |
| Encodage UTF-8 invalide | Exception capturée, message explicite |
| Saisie invalide (UI) | Message rouge dans le formulaire, refus de l'action |
| ID introuvable (CRUD) | ValueError capturé, messagebox d'erreur |

---

## Bibliothèques utilisées

| Bibliothèque | Rôle |
|-------------|------|
| `tkinter` | Interface graphique (inclus Python) |
| `customtkinter` | Widgets modernes (optionnel) |
| `json` | Sérialisation/désérialisation des données |
| `pathlib` | Gestion multiplateforme des chemins |
| `dataclasses` | Modèle de données `Tache` |
| `enum` | Énumérations `Priorite`, `Statut` |
| `datetime` | Manipulation des dates |
| `unittest` | Tests unitaires |
| `pytest` | Exécution des tests |

---

## Architecture POO

```
Tache (dataclass)       ← entité métier
Priorite (Enum)         ← niveau de priorité
Statut (Enum)           ← état de la tâche
TaskStorage             ← pattern Repository (lecture/écriture JSON)
TaskController          ← couche logique / contrôleur
AppTodoList (Tk)        ← interface principale
DialogueTache (Toplevel)← formulaire modal
StorageError            ← exception dédiée