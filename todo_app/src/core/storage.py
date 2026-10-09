"""
storage.py — Couche de persistance (pattern Repository)
=========================================================
Responsable de la lecture / écriture des tâches dans le fichier JSON.
Gère les erreurs de fichier, d'encodage et de format de manière robuste.

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import Tache


# ---------------------------------------------------------------------------
# Classe Storage
# ---------------------------------------------------------------------------

class TaskStorage:
    """
    Gère la persistance des tâches dans un fichier JSON.

    Méthodes principales
    --------------------
    charger()   → List[Tache]
    sauvegarder(taches: List[Tache]) → None
    """

    ENCODING = "utf-8"

    def __init__(self, chemin_fichier: Path) -> None:
        """
        Initialise le stockage avec le chemin du fichier JSON.

        Paramètres
        ----------
        chemin_fichier : Path
            Chemin complet vers le fichier de données (data/tasks.json).
        """
        self._chemin = Path(chemin_fichier)
        # Crée le dossier parent si nécessaire
        self._chemin.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def charger(self) -> List[Tache]:
        """
        Charge les tâches depuis le fichier JSON.

        Comportement en cas d'erreur
        ----------------------------
        - Fichier absent      → retourne une liste vide (premier démarrage).
        - JSON invalide       → lève StorageError avec message clair.
        - Données corrompues  → ignore les entrées malformées, log un avertissement.
        """
        if not self._chemin.exists():
            # Premier lancement : fichier absent → liste vide
            return []

        try:
            with open(self._chemin, "r", encoding=self.ENCODING) as f:
                contenu = f.read().strip()
        except PermissionError as e:
            raise StorageError(
                f"Impossible de lire le fichier '{self._chemin}' : permission refusée."
            ) from e
        except UnicodeDecodeError as e:
            raise StorageError(
                f"Erreur d'encodage dans '{self._chemin}'. "
                "Assurez-vous que le fichier est en UTF-8."
            ) from e

        if not contenu:
            return []

        try:
            donnees_brutes: list = json.loads(contenu)
        except json.JSONDecodeError as e:
            raise StorageError(
                f"Le fichier '{self._chemin}' est corrompu ou mal formé.\n"
                f"Détail : {e.msg} (ligne {e.lineno}, colonne {e.colno}).\n"
                "Vérifiez ou supprimez le fichier pour repartir à zéro."
            ) from e

        if not isinstance(donnees_brutes, list):
            raise StorageError(
                f"Format inattendu dans '{self._chemin}' : "
                "la racine JSON doit être une liste."
            )

        taches: List[Tache] = []
        avertissements: List[str] = []

        for i, entree in enumerate(donnees_brutes):
            try:
                tache = Tache.depuis_dict(entree)
                taches.append(tache)
            except (ValueError, KeyError, TypeError) as e:
                avertissements.append(
                    f"  • Entrée #{i + 1} ignorée : {e}"
                )

        if avertissements:
            print(
                f"[Storage] {len(avertissements)} entrée(s) ignorée(s) :\n"
                + "\n".join(avertissements)
            )

        return taches

    # ------------------------------------------------------------------
    # Écriture
    # ------------------------------------------------------------------

    def sauvegarder(self, taches: List[Tache]) -> None:
        """
        Sauvegarde la liste complète des tâches dans le fichier JSON.

        Utilise une écriture atomique (fichier temporaire + renommage)
        pour éviter la corruption en cas d'interruption.
        """
        donnees = [t.vers_dict() for t in taches]
        chemin_tmp = self._chemin.with_suffix(".tmp")

        try:
            with open(chemin_tmp, "w", encoding=self.ENCODING) as f:
                json.dump(donnees, f, ensure_ascii=False, indent=2)
            # Remplacement atomique
            chemin_tmp.replace(self._chemin)
        except PermissionError as e:
            raise StorageError(
                f"Impossible d'écrire dans '{self._chemin}' : permission refusée."
            ) from e
        except OSError as e:
            raise StorageError(
                f"Erreur système lors de la sauvegarde : {e}"
            ) from e
        finally:
            # Nettoyage du fichier temporaire en cas d'erreur
            if chemin_tmp.exists():
                chemin_tmp.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Export texte (tâches en retard / à faire)
    # ------------------------------------------------------------------

    def exporter_rapport(self, taches: List[Tache], chemin_sortie: Path) -> None:
        """
        Exporte dans un fichier texte les tâches en retard ou à faire.

        Paramètres
        ----------
        taches        : liste complète des tâches.
        chemin_sortie : chemin du fichier de sortie (output/rapport.txt).
        """
        from datetime import date as _date

        chemin_sortie = Path(chemin_sortie)
        chemin_sortie.parent.mkdir(parents=True, exist_ok=True)

        a_faire_ou_retard = [
            t for t in taches
            if t.statut.value in ("à faire", "en cours")
        ]
        en_retard = [t for t in a_faire_ou_retard if t.est_en_retard]
        a_faire   = [t for t in a_faire_ou_retard if not t.est_en_retard]

        lignes = [
            "=" * 60,
            "  RAPPORT DES TÂCHES — To-Do List Manager",
            f"  Généré le : {_date.today().isoformat()}",
            "=" * 60,
            "",
            f"Tâches EN RETARD ({len(en_retard)}) :",
            "-" * 40,
        ]
        if en_retard:
            for t in sorted(en_retard, key=lambda x: x.date_limite):
                lignes.append(
                    f"  [{t.id_tache}] {t.titre}\n"
                    f"       Priorité : {t.priorite.value} | "
                    f"Échéance : {t.date_limite} | "
                    f"Retard : {abs(t.jours_restants)} jour(s)"
                )
        else:
            lignes.append("  Aucune tâche en retard. ✓")

        lignes += [
            "",
            f"Tâches À FAIRE / EN COURS ({len(a_faire)}) :",
            "-" * 40,
        ]
        if a_faire:
            for t in sorted(a_faire, key=lambda x: (x.priorite.value, x.date_limite)):
                jours = t.jours_restants
                tag = f"{jours} jour(s) restant(s)" if jours >= 0 else "EXPIRÉ"
                lignes.append(
                    f"  [{t.id_tache}] {t.titre}\n"
                    f"       Priorité : {t.priorite.value} | "
                    f"Échéance : {t.date_limite} | {tag}"
                )
        else:
            lignes.append("  Aucune tâche en attente. ✓")

        lignes += ["", "=" * 60]

        try:
            with open(chemin_sortie, "w", encoding=self.ENCODING) as f:
                f.write("\n".join(lignes))
        except OSError as e:
            raise StorageError(f"Impossible d'écrire le rapport : {e}") from e


    # ------------------------------------------------------------------
    # Import fichier texte (.txt avec séparateur ;)
    # ------------------------------------------------------------------

    def importer_txt(self, chemin_txt: Path) -> dict:
        """
        Importe des tâches depuis un fichier texte (.txt) avec séparateur ';'.

        Format attendu
        --------------
        Ligne d'en-tête : id_tache;titre;priorite;date_limite;statut
        Lignes de données : une tâche par ligne, 5 colonnes séparées par ';'

        Retourne
        --------
        Un dictionnaire avec :
          - 'importees'   : liste des Tache importées avec succès
          - 'ignorees'    : liste de tuples (numéro_ligne, raison) pour les lignes invalides
          - 'total_lues'  : nombre total de lignes de données lues
        """
        chemin_txt = Path(chemin_txt)

        if not chemin_txt.exists():
            raise StorageError(
                f"Fichier introuvable : '{chemin_txt}'."
            )

        try:
            with open(chemin_txt, "r", encoding=self.ENCODING) as f:
                lignes = f.readlines()
        except PermissionError as e:
            raise StorageError(
                f"Permission refusée lors de la lecture de '{chemin_txt}'."
            ) from e
        except UnicodeDecodeError as e:
            raise StorageError(
                f"Erreur d'encodage dans '{chemin_txt}'. "
                "Assurez-vous que le fichier est en UTF-8."
            ) from e

        if not lignes:
            raise StorageError("Le fichier texte est vide.")

        # Ignorer la ligne d'en-tête
        lignes_donnees = lignes[1:]

        importees: list = []
        ignorees: list = []

        for i, ligne in enumerate(lignes_donnees, start=2):  # start=2 car ligne 1 = en-tête
            ligne = ligne.strip()
            if not ligne:
                continue  # Ignorer les lignes vides

            colonnes = ligne.split(";")

            # Vérification du nombre de colonnes
            if len(colonnes) != 5:
                ignorees.append((
                    i,
                    f"Nombre de colonnes incorrect ({len(colonnes)} au lieu de 5) : '{ligne}'"
                ))
                continue

            id_str, titre, priorite, date_limite, statut = [c.strip() for c in colonnes]

            # Validation id_tache
            try:
                id_tache = int(id_str)
            except ValueError:
                ignorees.append((i, f"Identifiant invalide : '{id_str}'"))
                continue

            # Construction de la tâche (déclenche toutes les validations de Tache)
            try:
                tache = Tache(
                    id_tache    = id_tache,
                    titre       = titre,
                    priorite    = priorite,
                    date_limite = date_limite,
                    statut      = statut,
                )
                importees.append(tache)
            except (ValueError, KeyError) as e:
                ignorees.append((i, str(e)))

        if importees:
            print(
                f"[Storage] Import TXT : {len(importees)} tâche(s) importée(s), "
                f"{len(ignorees)} ligne(s) ignorée(s)."
            )
        if ignorees:
            print("[Storage] Lignes ignorées :")
            for num, raison in ignorees:
                print(f"  • Ligne {num} : {raison}")

        return {
            "importees"  : importees,
            "ignorees"   : ignorees,
            "total_lues" : len(lignes_donnees),
        }


# ---------------------------------------------------------------------------
# Exception dédiée
# ---------------------------------------------------------------------------

class StorageError(Exception):
    """Exception levée par TaskStorage pour toute erreur de persistance."""
