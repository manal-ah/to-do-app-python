"""
main.py — Point d'entrée de l'application To-Do List
======================================================
Lance le contrôleur et l'interface graphique.

Usage :
    python main.py

"""

import sys
import tkinter.messagebox as mb
from pathlib import Path

# ── Résolution des chemins ────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DATA_DIR    = BASE_DIR / "data"
OUTPUT_DIR  = BASE_DIR / "output"

FICHIER_DONNEES = DATA_DIR  / "tasks.json"
FICHIER_RAPPORT = OUTPUT_DIR / "rapport.txt"

# ── Imports internes ──────────────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))
from src.core.logic   import TaskController
from src.core.storage import StorageError
from src.app          import AppTodoList


def main() -> None:
    """Initialise le contrôleur et lance la fenêtre principale."""
    # Crée les dossiers si nécessaire
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Chargement du contrôleur (gère FileNotFoundError en interne)
    try:
        ctrl = TaskController(
            chemin_donnees=FICHIER_DONNEES,
            chemin_sortie =FICHIER_RAPPORT,
        )
    except StorageError as e:
        # Erreur critique de lecture → afficher et quitter proprement
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            mb.showerror(
                "Erreur de démarrage",
                f"Impossible de charger les données :\n\n{e}\n\n"
                "Vérifiez ou supprimez le fichier data/tasks.json.",
            )
            root.destroy()
        except Exception:
            print(f"[ERREUR CRITIQUE] {e}", file=sys.stderr)
        sys.exit(1)

    # Lancement de l'interface
    app = AppTodoList(ctrl)
    app.mainloop()


if __name__ == "__main__":
    main()
