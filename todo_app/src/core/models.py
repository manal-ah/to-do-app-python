"""
models.py — Classes métiers de l'application To-Do List
========================================================
Contient la représentation des entités du domaine : Tâche (Task)
et la gestion des priorités/statuts via des énumérations.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Énumérations
# ---------------------------------------------------------------------------

class Priorite(str, Enum):
    """Niveaux de priorité d'une tâche."""
    BASSE   = "basse"
    MOYENNE = "moyenne"
    HAUTE   = "haute"

    @classmethod
    def liste_valeurs(cls) -> list[str]:
        """Retourne la liste des valeurs possibles (pour la validation UI)."""
        return [p.value for p in cls]


class Statut(str, Enum):
    """États possibles d'une tâche."""
    A_FAIRE    = "à faire"
    EN_COURS   = "en cours"
    TERMINEE   = "terminée"

    @classmethod
    def liste_valeurs(cls) -> list[str]:
        return [s.value for s in cls]


# ---------------------------------------------------------------------------
# Modèle principal
# ---------------------------------------------------------------------------

@dataclass
class Tache:
    """
    Représente une tâche dans la liste.

    Attributs
    ---------
    id_tache  : Identifiant unique (entier auto-incrémenté).
    titre     : Intitulé de la tâche (non vide).
    priorite  : Niveau de priorité (Priorite enum).
    date_limite : Date d'échéance (objet date Python).
    statut    : État courant de la tâche (Statut enum).
    """

    id_tache    : int
    titre       : str
    priorite    : Priorite
    date_limite : date
    statut      : Statut = field(default=Statut.A_FAIRE)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Valide les champs dès la construction de l'objet."""
        self._valider_titre(self.titre)
        if isinstance(self.priorite, str):
            self.priorite = Priorite(self.priorite.lower())
        if isinstance(self.statut, str):
            self.statut = Statut(self.statut.lower())
        if isinstance(self.date_limite, str):
            self.date_limite = datetime.strptime(self.date_limite, "%Y-%m-%d").date()

    # ------------------------------------------------------------------
    # Méthodes de validation statiques
    # ------------------------------------------------------------------

    @staticmethod
    def _valider_titre(titre: str) -> None:
        """Lève ValueError si le titre est vide ou trop long."""
        if not isinstance(titre, str) or not titre.strip():
            raise ValueError("Le titre de la tâche ne peut pas être vide.")
        if len(titre.strip()) > 120:
            raise ValueError("Le titre ne doit pas dépasser 120 caractères.")

    @staticmethod
    def valider_date(date_str: str) -> date:
        """
        Valide et convertit une chaîne 'YYYY-MM-DD' en objet date.
        Lève ValueError si le format est incorrect.
        """
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            raise ValueError(
                f"Format de date invalide : '{date_str}'. "
                "Utilisez le format YYYY-MM-DD (ex : 2026-05-01)."
            )

    # ------------------------------------------------------------------
    # Propriétés calculées
    # ------------------------------------------------------------------

    @property
    def est_en_retard(self) -> bool:
        """True si la tâche n'est pas terminée ET la date limite est dépassée."""
        return (
            self.statut != Statut.TERMINEE
            and self.date_limite < date.today()
        )

    @property
    def est_urgente(self) -> bool:
        """True si priorité HAUTE et tâche non terminée."""
        return self.priorite == Priorite.HAUTE and self.statut != Statut.TERMINEE

    @property
    def jours_restants(self) -> int:
        """Nombre de jours avant (ou après) la date limite."""
        return (self.date_limite - date.today()).days

    # ------------------------------------------------------------------
    # Sérialisation / Désérialisation
    # ------------------------------------------------------------------

    def vers_dict(self) -> dict:
        """Convertit la tâche en dictionnaire JSON-sérialisable."""
        return {
            "id_tache"    : self.id_tache,
            "titre"       : self.titre,
            "priorite"    : self.priorite.value,
            "date_limite" : self.date_limite.isoformat(),
            "statut"      : self.statut.value,
        }

    @classmethod
    def depuis_dict(cls, donnees: dict) -> "Tache":
        """
        Construit une Tache depuis un dictionnaire (lecture JSON).
        Lève ValueError / KeyError si les données sont malformées.
        """
        champs_requis = {"id_tache", "titre", "priorite", "date_limite", "statut"}
        champs_manquants = champs_requis - donnees.keys()
        if champs_manquants:
            raise ValueError(
                f"Champs manquants dans les données : {champs_manquants}"
            )
        return cls(
            id_tache    = int(donnees["id_tache"]),
            titre       = str(donnees["titre"]),
            priorite    = Priorite(str(donnees["priorite"]).lower()),
            date_limite = donnees["date_limite"],
            statut      = Statut(str(donnees["statut"]).lower()),
        )

    # ------------------------------------------------------------------
    # Représentation
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        retard_tag = " ⚠ EN RETARD" if self.est_en_retard else ""
        return (
            f"[{self.id_tache}] {self.titre} | "
            f"Priorité: {self.priorite.value} | "
            f"Échéance: {self.date_limite} | "
            f"Statut: {self.statut.value}{retard_tag}"
        )
