"""
tests/test_todo.py — Tests unitaires de l'application To-Do List
=================================================================
Couvre les couches models, storage et logic.

Lancer avec :  python -m pytest tests/ -v

"""

import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

# Résolution des chemins
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.models  import Priorite, Statut, Tache
from src.core.storage import StorageError, TaskStorage
from src.core.logic   import TaskController


# ---------------------------------------------------------------------------
# Tests — Modèles
# ---------------------------------------------------------------------------

class TestTache(unittest.TestCase):
    """Tests unitaires de la classe Tache."""

    def _tache_valide(self, **kwargs) -> Tache:
        defaults = dict(
            id_tache=1, titre="Tâche test",
            priorite=Priorite.MOYENNE,
            date_limite=date.today() + timedelta(days=7),
            statut=Statut.A_FAIRE,
        )
        defaults.update(kwargs)
        return Tache(**defaults)

    # ── Création valide ──────────────────────────────────────────────
    def test_creation_valide(self):
        t = self._tache_valide()
        self.assertEqual(t.titre, "Tâche test")
        self.assertEqual(t.priorite, Priorite.MOYENNE)
        self.assertEqual(t.statut, Statut.A_FAIRE)

    def test_creation_depuis_chaines(self):
        """__post_init__ doit convertir les chaînes en enums."""
        t = Tache(
            id_tache=2, titre="Test str",
            priorite="haute",
            date_limite=(date.today() + timedelta(days=3)).isoformat(),
            statut="en cours",
        )
        self.assertIsInstance(t.priorite, Priorite)
        self.assertIsInstance(t.statut, Statut)

    # ── Validation ───────────────────────────────────────────────────
    def test_titre_vide_leve_erreur(self):
        with self.assertRaises(ValueError):
            self._tache_valide(titre="")

    def test_titre_espaces_leve_erreur(self):
        with self.assertRaises(ValueError):
            self._tache_valide(titre="   ")

    def test_priorite_invalide_leve_erreur(self):
        with self.assertRaises(ValueError):
            self._tache_valide(priorite="extreme")

    def test_statut_invalide_leve_erreur(self):
        with self.assertRaises(ValueError):
            self._tache_valide(statut="en pause")

    def test_date_invalide_leve_erreur(self):
        with self.assertRaises(ValueError):
            Tache.valider_date("32/13/2026")

    def test_date_format_correct(self):
        d = Tache.valider_date("2026-12-31")
        self.assertEqual(d, date(2026, 12, 31))

    # ── Propriétés calculées ─────────────────────────────────────────
    def test_est_en_retard(self):
        t = self._tache_valide(
            date_limite=date.today() - timedelta(days=1)
        )
        self.assertTrue(t.est_en_retard)

    def test_pas_en_retard_si_terminee(self):
        t = self._tache_valide(
            date_limite=date.today() - timedelta(days=1),
            statut=Statut.TERMINEE,
        )
        self.assertFalse(t.est_en_retard)

    def test_est_urgente(self):
        t = self._tache_valide(priorite=Priorite.HAUTE)
        self.assertTrue(t.est_urgente)

    def test_pas_urgente_si_terminee(self):
        t = self._tache_valide(
            priorite=Priorite.HAUTE, statut=Statut.TERMINEE
        )
        self.assertFalse(t.est_urgente)

    # ── Sérialisation ────────────────────────────────────────────────
    def test_vers_dict_et_retour(self):
        t = self._tache_valide()
        d = t.vers_dict()
        t2 = Tache.depuis_dict(d)
        self.assertEqual(t.titre, t2.titre)
        self.assertEqual(t.priorite, t2.priorite)
        self.assertEqual(t.date_limite, t2.date_limite)

    def test_depuis_dict_champs_manquants(self):
        with self.assertRaises(ValueError):
            Tache.depuis_dict({"id_tache": 1, "titre": "X"})


# ---------------------------------------------------------------------------
# Tests — Storage
# ---------------------------------------------------------------------------

class TestTaskStorage(unittest.TestCase):
    """Tests de la persistance JSON."""

    def setUp(self):
        self.tmp_dir  = tempfile.TemporaryDirectory()
        self.chemin   = Path(self.tmp_dir.name) / "tasks.json"
        self.storage  = TaskStorage(self.chemin)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _tache(self, id_=1, retard=False) -> Tache:
        delta = -3 if retard else 5
        return Tache(
            id_tache=id_, titre=f"Tâche {id_}",
            priorite=Priorite.BASSE,
            date_limite=date.today() + timedelta(days=delta),
            statut=Statut.A_FAIRE,
        )

    def test_charger_fichier_absent(self):
        """Sans fichier → liste vide, pas d'exception."""
        self.assertFalse(self.chemin.exists())
        taches = self.storage.charger()
        self.assertEqual(taches, [])

    def test_sauvegarder_et_recharger(self):
        taches = [self._tache(1), self._tache(2)]
        self.storage.sauvegarder(taches)
        self.assertTrue(self.chemin.exists())
        rechargees = self.storage.charger()
        self.assertEqual(len(rechargees), 2)
        self.assertEqual(rechargees[0].titre, "Tâche 1")

    def test_json_corrompu_leve_storage_error(self):
        self.chemin.write_text("{invalide json[", encoding="utf-8")
        with self.assertRaises(StorageError):
            self.storage.charger()

    def test_fichier_vide_retourne_liste_vide(self):
        self.chemin.write_text("", encoding="utf-8")
        self.assertEqual(self.storage.charger(), [])

    def test_export_rapport(self):
        chemin_rapport = Path(self.tmp_dir.name) / "rapport.txt"
        taches = [self._tache(1, retard=True), self._tache(2, retard=False)]
        self.storage.exporter_rapport(taches, chemin_rapport)
        self.assertTrue(chemin_rapport.exists())
        contenu = chemin_rapport.read_text(encoding="utf-8")
        self.assertIn("RAPPORT", contenu)


# ---------------------------------------------------------------------------
# Tests — Logique / Contrôleur
# ---------------------------------------------------------------------------

class TestTaskController(unittest.TestCase):
    """Tests d'intégration de la couche contrôleur."""

    def setUp(self):
        self.tmp_dir  = tempfile.TemporaryDirectory()
        base          = Path(self.tmp_dir.name)
        self.ctrl     = TaskController(
            chemin_donnees = base / "tasks.json",
            chemin_sortie  = base / "rapport.txt",
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _creer(self, titre="T", prio="moyenne", delta=7, statut="à faire"):
        d = (date.today() + timedelta(days=delta)).isoformat()
        return self.ctrl.creer_tache(titre, prio, d, statut)

    # ── CRUD ─────────────────────────────────────────────────────────
    def test_creer_tache(self):
        t = self._creer("Tâche A")
        self.assertEqual(t.titre, "Tâche A")
        self.assertEqual(len(self.ctrl.obtenir_toutes()), 1)

    def test_ids_auto_incrementes(self):
        t1 = self._creer("T1")
        t2 = self._creer("T2")
        self.assertNotEqual(t1.id_tache, t2.id_tache)

    def test_modifier_tache(self):
        t = self._creer("Avant")
        self.ctrl.modifier_tache(t.id_tache, titre="Après")
        self.assertEqual(self.ctrl.obtenir_par_id(t.id_tache).titre, "Après")

    def test_supprimer_tache(self):
        t = self._creer()
        self.ctrl.supprimer_tache(t.id_tache)
        self.assertIsNone(self.ctrl.obtenir_par_id(t.id_tache))

    def test_supprimer_id_inconnu(self):
        with self.assertRaises(ValueError):
            self.ctrl.supprimer_tache(9999)

    def test_modifier_id_inconnu(self):
        with self.assertRaises(ValueError):
            self.ctrl.modifier_tache(9999, titre="X")

    # ── Validation ───────────────────────────────────────────────────
    def test_creer_titre_vide_refuse(self):
        with self.assertRaises(ValueError):
            self._creer(titre="")

    def test_creer_date_invalide_refuse(self):
        with self.assertRaises(ValueError):
            self.ctrl.creer_tache("T", "basse", "mauvaise-date")

    def test_creer_priorite_invalide_refuse(self):
        with self.assertRaises(ValueError):
            self._creer(prio="super-urgente")

    # ── Recherche & filtre ────────────────────────────────────────────
    def test_rechercher_terme(self):
        self._creer("Python POO")
        self._creer("Base de données")
        r = self.ctrl.rechercher("python")
        self.assertEqual(len(r), 1)
        self.assertIn("Python", r[0].titre)

    def test_filtrer_par_priorite(self):
        self._creer("H", prio="haute")
        self._creer("B", prio="basse")
        r = self.ctrl.filtrer(priorite="haute")
        self.assertTrue(all(t.priorite.value == "haute" for t in r))

    def test_filtrer_urgentes(self):
        self._creer("U", prio="haute")
        self._creer("N", prio="basse")
        r = self.ctrl.filtrer(urgentes_seulement=True)
        self.assertTrue(all(t.est_urgente for t in r))

    def test_filtrer_en_retard(self):
        self._creer("Passée", delta=-5)
        self._creer("Future", delta=5)
        r = self.ctrl.filtrer(en_retard_seulement=True)
        self.assertTrue(all(t.est_en_retard for t in r))

    # ── Statistiques ─────────────────────────────────────────────────
    def test_statistiques(self):
        self._creer("T1", statut="à faire")
        self._creer("T2", statut="terminée")
        stats = self.ctrl.statistiques()
        self.assertEqual(stats["total"],    2)
        self.assertEqual(stats["terminees"], 1)
        self.assertEqual(stats["a_faire"],   1)

    # ── Persistance ──────────────────────────────────────────────────
    def test_persistance_entre_redemarrages(self):
        """Les données ajoutées doivent survivre à un redémarrage."""
        t = self._creer("Persistée")
        id_ = t.id_tache

        # Recharge depuis le même fichier
        ctrl2 = TaskController(
            chemin_donnees=self.ctrl._storage._chemin,
            chemin_sortie=self.ctrl._storage._chemin.parent / "r.txt",
        )
        self.assertIsNotNone(ctrl2.obtenir_par_id(id_))
        self.assertEqual(ctrl2.obtenir_par_id(id_).titre, "Persistée")


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
