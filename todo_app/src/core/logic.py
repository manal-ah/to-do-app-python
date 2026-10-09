"""
logic.py — Couche contrôleur (logique métier)
==============================================
Sépare la manipulation des données de l'interface graphique.
Toute opération CRUD, filtre, recherche et export passe par ce module.

"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Optional

from .models import Priorite, Statut, Tache
from .storage import StorageError, TaskStorage


# ---------------------------------------------------------------------------
# Contrôleur principal
# ---------------------------------------------------------------------------

class TaskController:
    """
    Contrôleur centralisé pour la gestion des tâches.

    Responsabilités
    ---------------
    - Maintenir la liste en mémoire (self._taches).
    - Déléguer la persistance à TaskStorage.
    - Exposer des méthodes CRUD propres à l'interface.
    - Valider la cohérence des données avant toute modification.
    """

    def __init__(self, chemin_donnees: Path, chemin_sortie: Path) -> None:
        self._storage   = TaskStorage(chemin_donnees)
        self._sortie    = Path(chemin_sortie)
        self._taches    : List[Tache] = []
        self._prochain_id: int = 1
        self._charger_depuis_fichier()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _charger_depuis_fichier(self) -> None:
        """Charge les tâches depuis le fichier au démarrage."""
        self._taches = self._storage.charger()
        if self._taches:
            self._prochain_id = max(t.id_tache for t in self._taches) + 1
        else:
            self._prochain_id = 1

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def obtenir_toutes(self) -> List[Tache]:
        """Retourne une copie de la liste complète des tâches."""
        return list(self._taches)

    def obtenir_par_id(self, id_tache: int) -> Optional[Tache]:
        """Retourne la tâche correspondant à l'identifiant, ou None."""
        for t in self._taches:
            if t.id_tache == id_tache:
                return t
        return None

    def rechercher(self, terme: str) -> List[Tache]:
        """Recherche insensible à la casse dans le titre des tâches."""
        terme = terme.strip().lower()
        if not terme:
            return list(self._taches)
        return [t for t in self._taches if terme in t.titre.lower()]

    def filtrer(
        self,
        priorite: Optional[str] = None,
        statut:   Optional[str] = None,
        urgentes_seulement: bool = False,
        en_retard_seulement: bool = False,
    ) -> List[Tache]:
        """
        Filtre les tâches selon plusieurs critères combinables.

        Paramètres
        ----------
        priorite            : valeur Priorite (ex : 'haute') ou None.
        statut              : valeur Statut   (ex : 'à faire') ou None.
        urgentes_seulement  : ne retourner que les tâches urgentes.
        en_retard_seulement : ne retourner que les tâches en retard.
        """
        resultats = list(self._taches)

        if priorite:
            try:
                p = Priorite(priorite.lower())
                resultats = [t for t in resultats if t.priorite == p]
            except ValueError:
                raise ValueError(
                    f"Priorité invalide : '{priorite}'. "
                    f"Valeurs acceptées : {Priorite.liste_valeurs()}."
                )

        if statut:
            try:
                s = Statut(statut.lower())
                resultats = [t for t in resultats if t.statut == s]
            except ValueError:
                raise ValueError(
                    f"Statut invalide : '{statut}'. "
                    f"Valeurs acceptées : {Statut.liste_valeurs()}."
                )

        if urgentes_seulement:
            resultats = [t for t in resultats if t.est_urgente]

        if en_retard_seulement:
            resultats = [t for t in resultats if t.est_en_retard]

        return resultats

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------

    def creer_tache(
        self,
        titre:       str,
        priorite:    str,
        date_limite: str,
        statut:      str = "à faire",
    ) -> Tache:
        """
        Crée et enregistre une nouvelle tâche après validation.

        Lève ValueError si l'un des champs est invalide.
        """
        # Validation date
        date_obj = Tache.valider_date(date_limite)

        # Construction (déclenche __post_init__ → validation)
        nouvelle = Tache(
            id_tache    = self._prochain_id,
            titre       = titre.strip(),
            priorite    = priorite,
            date_limite = date_obj,
            statut      = statut,
        )

        self._taches.append(nouvelle)
        self._prochain_id += 1
        self._sauvegarder()
        return nouvelle

    # ------------------------------------------------------------------
    # Modification
    # ------------------------------------------------------------------

    def modifier_tache(
        self,
        id_tache:    int,
        titre:       Optional[str] = None,
        priorite:    Optional[str] = None,
        date_limite: Optional[str] = None,
        statut:      Optional[str] = None,
    ) -> Tache:
        """
        Modifie les champs fournis d'une tâche existante.

        Lève ValueError si l'id est inconnu ou si un champ est invalide.
        """
        tache = self.obtenir_par_id(id_tache)
        if tache is None:
            raise ValueError(f"Aucune tâche avec l'identifiant {id_tache}.")

        if titre is not None:
            Tache._valider_titre(titre)
            tache.titre = titre.strip()

        if priorite is not None:
            try:
                tache.priorite = Priorite(priorite.lower())
            except ValueError:
                raise ValueError(
                    f"Priorité invalide : '{priorite}'. "
                    f"Valeurs acceptées : {Priorite.liste_valeurs()}."
                )

        if date_limite is not None:
            tache.date_limite = Tache.valider_date(date_limite)

        if statut is not None:
            try:
                tache.statut = Statut(statut.lower())
            except ValueError:
                raise ValueError(
                    f"Statut invalide : '{statut}'. "
                    f"Valeurs acceptées : {Statut.liste_valeurs()}."
                )

        self._sauvegarder()
        return tache

    def changer_statut(self, id_tache: int, nouveau_statut: str) -> Tache:
        """Raccourci pour changer uniquement le statut d'une tâche."""
        return self.modifier_tache(id_tache, statut=nouveau_statut)

    # ------------------------------------------------------------------
    # Suppression
    # ------------------------------------------------------------------

    def supprimer_tache(self, id_tache: int) -> None:
        """
        Supprime définitivement une tâche par son identifiant.
        Lève ValueError si la tâche est introuvable.
        """
        tache = self.obtenir_par_id(id_tache)
        if tache is None:
            raise ValueError(f"Aucune tâche avec l'identifiant {id_tache}.")
        self._taches.remove(tache)
        self._sauvegarder()

    # ------------------------------------------------------------------
    # Export rapport
    # ------------------------------------------------------------------

    def exporter_rapport(self) -> Path:
        """
        Génère le rapport texte dans output/ et retourne le chemin.
        """
        self._storage.exporter_rapport(self._taches, self._sortie)
        return self._sortie

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------

    def statistiques(self) -> dict:
        """Retourne un dictionnaire de statistiques sur les tâches."""
        total = len(self._taches)
        return {
            "total"        : total,
            "a_faire"      : sum(1 for t in self._taches if t.statut == Statut.A_FAIRE),
            "en_cours"     : sum(1 for t in self._taches if t.statut == Statut.EN_COURS),
            "terminees"    : sum(1 for t in self._taches if t.statut == Statut.TERMINEE),
            "en_retard"    : sum(1 for t in self._taches if t.est_en_retard),
            "urgentes"     : sum(1 for t in self._taches if t.est_urgente),
            "haute"        : sum(1 for t in self._taches if t.priorite == Priorite.HAUTE),
            "moyenne"      : sum(1 for t in self._taches if t.priorite == Priorite.MOYENNE),
            "basse"        : sum(1 for t in self._taches if t.priorite == Priorite.BASSE),
        }

    # ------------------------------------------------------------------
    # Import fichier texte
    # ------------------------------------------------------------------

    def importer_depuis_txt(self, chemin_txt: Path) -> dict:
        """
        Importe des tâches depuis un fichier .txt (séparateur ';').

        Les tâches valides sont ajoutées à la liste en mémoire
        avec de nouveaux identifiants pour éviter les doublons.

        Retourne le rapport d'import : importees, ignorees, total_lues.
        """
        rapport = self._storage.importer_txt(chemin_txt)

        ajoutees = []
        for tache in rapport["importees"]:
            # Assigner un nouvel id pour éviter tout conflit
            tache.id_tache = self._prochain_id
            self._prochain_id += 1
            self._taches.append(tache)
            ajoutees.append(tache)

        if ajoutees:
            self._sauvegarder()

        rapport["importees"] = ajoutees
        return rapport

    # ------------------------------------------------------------------
    # Interne
    # ------------------------------------------------------------------

    def _sauvegarder(self) -> None:
        """Sauvegarde automatique après chaque modification."""
        self._storage.sauvegarder(self._taches)
