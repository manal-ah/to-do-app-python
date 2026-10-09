"""
app.py — Interface graphique (customTkinter)
=============================================
Fournit une UI moderne pour gérer les tâches.
La logique métier est entièrement déléguée à TaskController.

Auteur  : Projet IA-2 — Université Ibn Zohr, Agadir
"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.messagebox as mb
import tkinter.ttk as ttk
from pathlib import Path
from typing import Optional

# ── CustomTkinter ────────────────────────────────────────────────────────────
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False

# ── Couche métier ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.logic import TaskController
from src.core.models import Priorite, Statut
from src.core.storage import StorageError

# ---------------------------------------------------------------------------
# Constantes de design
# ---------------------------------------------------------------------------

COULEURS = {
    "bg_principal"  : "#1e1e2e",
    "bg_panneau"    : "#2a2a3e",
    "bg_carte"      : "#313149",
    "accent"        : "#7c6af7",
    "accent_hover"  : "#9b8bf9",
    "succes"        : "#22c55e",
    "danger"        : "#ef4444",
    "warning"       : "#f59e0b",
    "texte_clair"   : "#e2e8f0",
    "texte_gris"    : "#94a3b8",
    "separateur"    : "#3f3f5e",
    "retard"        : "#fee2e2",
    "urgent_bg"     : "#fff7ed",
}

POLICE_TITRE  = ("Segoe UI", 22, "bold")
POLICE_SOUS   = ("Segoe UI", 13, "bold")
POLICE_CORPS  = ("Segoe UI", 11)
POLICE_PETITE = ("Segoe UI", 10)
POLICE_MONO   = ("Consolas", 10)

PRIORITE_COULEURS = {
    "haute"   : "#ef4444",
    "moyenne" : "#f59e0b",
    "basse"   : "#22c55e",
}

STATUT_ICONE = {
    "à faire"  : "⬜",
    "en cours" : "🔄",
    "terminée" : "✅",
}


# ---------------------------------------------------------------------------
# Fenêtre de dialogue : Ajouter / Modifier une tâche
# ---------------------------------------------------------------------------

class DialogueTache(tk.Toplevel):
    """Fenêtre modale pour créer ou éditer une tâche."""

    def __init__(self, parent: "AppTodoList", tache=None) -> None:
        super().__init__(parent)
        self.parent_app = parent
        self.tache      = tache           # None → création, sinon → édition
        self.resultat   = None            # Dict rempli si l'utilisateur confirme

        # ── Fenêtre ──────────────────────────────────────────────────────────
        mode = "Modifier la tâche" if tache else "Nouvelle tâche"
        self.title(mode)
        self.configure(bg=COULEURS["bg_panneau"])
        self.resizable(False, False)
        self.grab_set()                   # Bloque la fenêtre principale

        self._construire_ui(mode)

        # Remplissage si édition
        if tache:
            self._remplir(tache)

        self.geometry("460x400")
        self._centrer()

    # ------------------------------------------------------------------
    def _centrer(self) -> None:
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width()  - self.winfo_width())  // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    def _construire_ui(self, titre: str) -> None:
        # En-tête
        tk.Label(
            self, text=titre, font=POLICE_SOUS,
            bg=COULEURS["bg_panneau"], fg=COULEURS["accent"]
        ).pack(pady=(18, 10))

        corps = tk.Frame(self, bg=COULEURS["bg_panneau"])
        corps.pack(fill="both", expand=True, padx=28, pady=4)

        def champ(parent, label_texte, row):
            tk.Label(
                parent, text=label_texte, font=POLICE_CORPS,
                bg=COULEURS["bg_panneau"], fg=COULEURS["texte_gris"],
                anchor="w"
            ).grid(row=row, column=0, sticky="w", pady=5)

        # Titre
        champ(corps, "Titre *", 0)
        self.var_titre = tk.StringVar()
        e = tk.Entry(
            corps, textvariable=self.var_titre, font=POLICE_CORPS,
            bg=COULEURS["bg_carte"], fg=COULEURS["texte_clair"],
            insertbackground=COULEURS["texte_clair"],
            relief="flat", bd=0, width=32
        )
        e.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5, ipady=4)
        e.focus_set()

        # Priorité
        champ(corps, "Priorité *", 1)
        self.var_priorite = tk.StringVar(value="moyenne")
        cb_prio = ttk.Combobox(
            corps, textvariable=self.var_priorite,
            values=Priorite.liste_valeurs(), state="readonly",
            font=POLICE_CORPS, width=30
        )
        cb_prio.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5, ipady=3)

        # Date limite
        champ(corps, "Date limite *\n(YYYY-MM-DD)", 2)
        self.var_date = tk.StringVar()
        tk.Entry(
            corps, textvariable=self.var_date, font=POLICE_CORPS,
            bg=COULEURS["bg_carte"], fg=COULEURS["texte_clair"],
            insertbackground=COULEURS["texte_clair"],
            relief="flat", bd=0, width=32
        ).grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=5, ipady=4)

        # Statut
        champ(corps, "Statut", 3)
        self.var_statut = tk.StringVar(value="à faire")
        ttk.Combobox(
            corps, textvariable=self.var_statut,
            values=Statut.liste_valeurs(), state="readonly",
            font=POLICE_CORPS, width=30
        ).grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=5, ipady=3)

        corps.columnconfigure(1, weight=1)

        # Message d'erreur
        self.var_erreur = tk.StringVar()
        tk.Label(
            self, textvariable=self.var_erreur, font=POLICE_PETITE,
            bg=COULEURS["bg_panneau"], fg=COULEURS["danger"],
            wraplength=400, justify="left"
        ).pack(padx=28, fill="x")

        # Boutons
        barre = tk.Frame(self, bg=COULEURS["bg_panneau"])
        barre.pack(fill="x", padx=28, pady=(6, 18))

        tk.Button(
            barre, text="Annuler", font=POLICE_CORPS,
            bg=COULEURS["separateur"], fg=COULEURS["texte_gris"],
            activebackground=COULEURS["bg_carte"], relief="flat",
            cursor="hand2", padx=14, pady=6,
            command=self.destroy
        ).pack(side="right", padx=(6, 0))

        label_btn = "💾  Enregistrer" if self.tache else "➕  Ajouter"
        tk.Button(
            barre, text=label_btn, font=POLICE_CORPS,
            bg=COULEURS["accent"], fg="white",
            activebackground=COULEURS["accent_hover"], relief="flat",
            cursor="hand2", padx=14, pady=6,
            command=self._valider
        ).pack(side="right")

    # ------------------------------------------------------------------
    def _remplir(self, tache) -> None:
        self.var_titre.set(tache.titre)
        self.var_priorite.set(tache.priorite.value)
        self.var_date.set(tache.date_limite.isoformat())
        self.var_statut.set(tache.statut.value)

    # ------------------------------------------------------------------
    def _valider(self) -> None:
        self.var_erreur.set("")
        titre    = self.var_titre.get().strip()
        priorite = self.var_priorite.get()
        date_str = self.var_date.get().strip()
        statut   = self.var_statut.get()

        # Vérifications basiques
        if not titre:
            self.var_erreur.set("⚠ Le titre est obligatoire.")
            return
        if not date_str:
            self.var_erreur.set("⚠ La date limite est obligatoire.")
            return

        self.resultat = {
            "titre"       : titre,
            "priorite"    : priorite,
            "date_limite" : date_str,
            "statut"      : statut,
        }
        self.destroy()


# ---------------------------------------------------------------------------
# Fenêtre principale
# ---------------------------------------------------------------------------

class AppTodoList(tk.Tk):
    """Application principale To-Do List."""

    def __init__(self, controller: TaskController) -> None:
        super().__init__()
        self.ctrl = controller

        self.title("📋  To-Do List Manager — IA-2 Python Project")
        self.configure(bg=COULEURS["bg_principal"])
        self.geometry("1100x700")
        self.minsize(900, 560)

        # Variables de filtre
        self.var_recherche   = tk.StringVar()
        self.var_filtre_prio = tk.StringVar(value="Toutes")
        self.var_filtre_stat = tk.StringVar(value="Tous")
        self.var_urgentes    = tk.BooleanVar(value=False)
        self.var_retard      = tk.BooleanVar(value=False)

        self._style_ttk()
        self._construire_ui()
        self._rafraichir_liste()
        self._rafraichir_stats()

        # Raccourcis clavier
        self.bind("<Control-n>", lambda _: self._ajouter())
        self.bind("<Delete>",    lambda _: self._supprimer())
        self.bind("<F5>",        lambda _: self._rafraichir_liste())

    # ------------------------------------------------------------------
    # Style ttk (Treeview)
    # ------------------------------------------------------------------

    def _style_ttk(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Todo.Treeview",
            background   = COULEURS["bg_carte"],
            foreground   = COULEURS["texte_clair"],
            fieldbackground = COULEURS["bg_carte"],
            rowheight    = 34,
            font         = POLICE_CORPS,
            borderwidth  = 0,
        )
        style.configure("Todo.Treeview.Heading",
            background = COULEURS["bg_panneau"],
            foreground = COULEURS["accent"],
            font       = ("Segoe UI", 11, "bold"),
            relief     = "flat",
        )
        style.map("Todo.Treeview",
            background=[("selected", COULEURS["accent"])],
            foreground=[("selected", "white")],
        )
        style.configure("TCombobox",
            fieldbackground = COULEURS["bg_carte"],
            background      = COULEURS["bg_carte"],
            foreground      = COULEURS["texte_clair"],
            arrowcolor      = COULEURS["accent"],
        )

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _construire_ui(self) -> None:
        # ── Barre de titre ───────────────────────────────────────────────
        barre_titre = tk.Frame(self, bg=COULEURS["bg_panneau"], height=56)
        barre_titre.pack(fill="x", side="top")
        barre_titre.pack_propagate(False)

        tk.Label(
            barre_titre,
            text="📋  To-Do List Manager",
            font=POLICE_TITRE,
            bg=COULEURS["bg_panneau"],
            fg=COULEURS["texte_clair"],
        ).pack(side="left", padx=22, pady=10)

        # Bouton export
        tk.Button(
            barre_titre, text="📤  Exporter rapport",
            font=POLICE_CORPS, bg=COULEURS["bg_carte"],
            fg=COULEURS["texte_clair"], relief="flat",
            activebackground=COULEURS["separateur"],
            cursor="hand2", padx=12, pady=5,
            command=self._exporter_rapport
        ).pack(side="right", padx=14, pady=10)

        # Bouton import TXT
        tk.Button(
            barre_titre, text="📂  Importer .txt",
            font=POLICE_CORPS, bg=COULEURS["succes"],
            fg="white", relief="flat",
            activebackground="#16a34a",
            cursor="hand2", padx=12, pady=5,
            command=self._importer_txt
        ).pack(side="right", padx=(0, 4), pady=10)

        # ── Corps (panneau gauche + droite) ──────────────────────────────
        corps = tk.Frame(self, bg=COULEURS["bg_principal"])
        corps.pack(fill="both", expand=True)

        # ── Panneau gauche (filtres + stats) ─────────────────────────────
        panneau_g = tk.Frame(corps, bg=COULEURS["bg_panneau"], width=230)
        panneau_g.pack(side="left", fill="y", padx=(10, 0), pady=10)
        panneau_g.pack_propagate(False)
        self._construire_panneau_gauche(panneau_g)

        # ── Panneau droit (liste des tâches) ─────────────────────────────
        panneau_d = tk.Frame(corps, bg=COULEURS["bg_principal"])
        panneau_d.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self._construire_panneau_droit(panneau_d)

    # ------------------------------------------------------------------
    def _construire_panneau_gauche(self, parent: tk.Frame) -> None:
        def section(texte):
            tk.Label(
                parent, text=texte.upper(), font=("Segoe UI", 9, "bold"),
                bg=COULEURS["bg_panneau"], fg=COULEURS["texte_gris"]
            ).pack(anchor="w", padx=14, pady=(14, 3))
            tk.Frame(parent, bg=COULEURS["separateur"], height=1).pack(fill="x", padx=14)

        # ── Filtres ─────────────────────────────────────────────────────
        section("Filtres")

        # Priorité
        tk.Label(parent, text="Priorité", font=POLICE_PETITE,
                 bg=COULEURS["bg_panneau"], fg=COULEURS["texte_gris"]
                 ).pack(anchor="w", padx=14, pady=(8, 2))
        cb_prio = ttk.Combobox(
            parent, textvariable=self.var_filtre_prio,
            values=["Toutes"] + Priorite.liste_valeurs(),
            state="readonly", font=POLICE_PETITE, width=22
        )
        cb_prio.pack(padx=14, fill="x")
        cb_prio.bind("<<ComboboxSelected>>", lambda _: self._rafraichir_liste())

        # Statut
        tk.Label(parent, text="Statut", font=POLICE_PETITE,
                 bg=COULEURS["bg_panneau"], fg=COULEURS["texte_gris"]
                 ).pack(anchor="w", padx=14, pady=(8, 2))
        cb_stat = ttk.Combobox(
            parent, textvariable=self.var_filtre_stat,
            values=["Tous"] + Statut.liste_valeurs(),
            state="readonly", font=POLICE_PETITE, width=22
        )
        cb_stat.pack(padx=14, fill="x")
        cb_stat.bind("<<ComboboxSelected>>", lambda _: self._rafraichir_liste())

        # Urgentes / En retard
        tk.Checkbutton(
            parent, text="⚡  Urgentes seulement", font=POLICE_PETITE,
            variable=self.var_urgentes, bg=COULEURS["bg_panneau"],
            fg=COULEURS["texte_clair"], selectcolor=COULEURS["bg_carte"],
            activebackground=COULEURS["bg_panneau"],
            command=self._rafraichir_liste
        ).pack(anchor="w", padx=14, pady=(10, 2))

        tk.Checkbutton(
            parent, text="⏰  En retard seulement", font=POLICE_PETITE,
            variable=self.var_retard, bg=COULEURS["bg_panneau"],
            fg=COULEURS["texte_clair"], selectcolor=COULEURS["bg_carte"],
            activebackground=COULEURS["bg_panneau"],
            command=self._rafraichir_liste
        ).pack(anchor="w", padx=14, pady=(2, 10))

        tk.Button(
            parent, text="🔄  Réinitialiser filtres",
            font=POLICE_PETITE, bg=COULEURS["bg_carte"],
            fg=COULEURS["texte_gris"], relief="flat",
            cursor="hand2", padx=8, pady=4,
            command=self._reinit_filtres
        ).pack(padx=14, fill="x", pady=(0, 12))

        # ── Statistiques ─────────────────────────────────────────────────
        section("Statistiques")
        self.frame_stats = tk.Frame(parent, bg=COULEURS["bg_panneau"])
        self.frame_stats.pack(fill="x", padx=14, pady=8)

    # ------------------------------------------------------------------
    def _construire_panneau_droit(self, parent: tk.Frame) -> None:
        # ── Barre de recherche ───────────────────────────────────────────
        barre = tk.Frame(parent, bg=COULEURS["bg_principal"])
        barre.pack(fill="x", pady=(0, 8))

        tk.Label(barre, text="🔍", font=("Segoe UI", 13),
                 bg=COULEURS["bg_principal"], fg=COULEURS["texte_gris"]
                 ).pack(side="left")

        tk.Entry(
            barre, textvariable=self.var_recherche,
            font=POLICE_CORPS, bg=COULEURS["bg_carte"],
            fg=COULEURS["texte_clair"], insertbackground=COULEURS["texte_clair"],
            relief="flat", bd=0
        ).pack(side="left", fill="x", expand=True, ipady=5, padx=(4, 10))

        self.var_recherche.trace_add("write", lambda *_: self._rafraichir_liste())

        # Boutons CRUD
        for texte, couleur, cmd in [
            ("➕  Ajouter",    COULEURS["accent"],  self._ajouter),
            ("✏️  Modifier",   COULEURS["bg_carte"], self._modifier),
            ("🗑️  Supprimer",  COULEURS["danger"],  self._supprimer),
        ]:
            tk.Button(
                barre, text=texte, font=POLICE_CORPS,
                bg=couleur, fg="white",
                activebackground=COULEURS["accent_hover"],
                relief="flat", cursor="hand2", padx=10, pady=5,
                command=cmd
            ).pack(side="left", padx=3)

        # ── Tableau des tâches ───────────────────────────────────────────
        frame_tree = tk.Frame(parent, bg=COULEURS["bg_principal"])
        frame_tree.pack(fill="both", expand=True)

        colonnes = ("id", "titre", "priorite", "date_limite", "statut", "jours")
        self.tree = ttk.Treeview(
            frame_tree, columns=colonnes,
            show="headings", style="Todo.Treeview",
            selectmode="browse"
        )

        entetes = {
            "id"         : ("#",            50,  "center"),
            "titre"      : ("Titre",        370, "w"),
            "priorite"   : ("Priorité",     90,  "center"),
            "date_limite": ("Échéance",     110, "center"),
            "statut"     : ("Statut",       110, "center"),
            "jours"      : ("Jours rest.",  85,  "center"),
        }
        for col, (hdr, w, anch) in entetes.items():
            self.tree.heading(col, text=hdr,
                              command=lambda c=col: self._trier(c))
            self.tree.column(col, width=w, anchor=anch, minwidth=40)

        # Tags de couleur
        self.tree.tag_configure("retard",   background="#3d1515", foreground="#fca5a5")
        self.tree.tag_configure("urgent",   background="#3d2e05", foreground="#fcd34d")
        self.tree.tag_configure("terminee", background="#0f2d1a", foreground="#86efac")
        self.tree.tag_configure("normal",   background=COULEURS["bg_carte"],
                                            foreground=COULEURS["texte_clair"])

        # Scrollbar
        sb = ttk.Scrollbar(frame_tree, orient="vertical",
                           command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Double-clic → modifier
        self.tree.bind("<Double-1>", lambda _: self._modifier())

        # ── Barre de statut ──────────────────────────────────────────────
        self.var_status = tk.StringVar(value="Prêt.")
        tk.Label(
            parent, textvariable=self.var_status,
            font=POLICE_PETITE, bg=COULEURS["bg_principal"],
            fg=COULEURS["texte_gris"], anchor="w"
        ).pack(fill="x", pady=(4, 0))

    # ------------------------------------------------------------------
    # Rafraîchissement
    # ------------------------------------------------------------------

    def _rafraichir_liste(self) -> None:
        """Recharge la liste selon les filtres actifs."""
        terme    = self.var_recherche.get().strip()
        prio_val = self.var_filtre_prio.get()
        stat_val = self.var_filtre_stat.get()
        urgentes = self.var_urgentes.get()
        retard   = self.var_retard.get()

        try:
            # Recherche textuelle
            taches = (
                self.ctrl.rechercher(terme) if terme
                else self.ctrl.obtenir_toutes()
            )

            # Filtres supplémentaires
            if prio_val != "Toutes":
                from src.core.models import Priorite as P
                taches = [t for t in taches if t.priorite.value == prio_val]
            if stat_val != "Tous":
                from src.core.models import Statut as S
                taches = [t for t in taches if t.statut.value == stat_val]
            if urgentes:
                taches = [t for t in taches if t.est_urgente]
            if retard:
                taches = [t for t in taches if t.est_en_retard]

        except ValueError as e:
            self._status(f"⚠ Filtre : {e}", erreur=True)
            return

        # Effacer et repeupler
        for item in self.tree.get_children():
            self.tree.delete(item)

        for t in taches:
            jours = t.jours_restants
            if jours < 0:
                jours_str = f"−{abs(jours)} j"
            elif jours == 0:
                jours_str = "Aujourd'hui"
            else:
                jours_str = f"+{jours} j"

            icone = STATUT_ICONE.get(t.statut.value, "")

            if t.est_en_retard:
                tag = "retard"
            elif t.est_urgente:
                tag = "urgent"
            elif t.statut.value == "terminée":
                tag = "terminee"
            else:
                tag = "normal"

            self.tree.insert("", "end", iid=str(t.id_tache), tags=(tag,), values=(
                t.id_tache,
                t.titre,
                t.priorite.value.capitalize(),
                t.date_limite.isoformat(),
                f"{icone} {t.statut.value}",
                jours_str,
            ))

        n = len(taches)
        self._status(f"{n} tâche(s) affichée(s).")
        self._rafraichir_stats()

    def _rafraichir_stats(self) -> None:
        """Met à jour le panneau de statistiques."""
        for w in self.frame_stats.winfo_children():
            w.destroy()

        stats = self.ctrl.statistiques()
        lignes = [
            ("Total",       stats["total"],      COULEURS["texte_clair"]),
            ("À faire",     stats["a_faire"],    COULEURS["texte_clair"]),
            ("En cours",    stats["en_cours"],   COULEURS["warning"]),
            ("Terminées",   stats["terminees"],  COULEURS["succes"]),
            ("En retard",   stats["en_retard"],  COULEURS["danger"]),
            ("Urgentes",    stats["urgentes"],   COULEURS["warning"]),
        ]
        for label, valeur, couleur in lignes:
            f = tk.Frame(self.frame_stats, bg=COULEURS["bg_panneau"])
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, font=POLICE_PETITE,
                     bg=COULEURS["bg_panneau"],
                     fg=COULEURS["texte_gris"]).pack(side="left")
            tk.Label(f, text=str(valeur), font=("Segoe UI", 10, "bold"),
                     bg=COULEURS["bg_panneau"],
                     fg=couleur).pack(side="right")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _ajouter(self) -> None:
        dlg = DialogueTache(self)
        self.wait_window(dlg)
        if not dlg.resultat:
            return
        try:
            t = self.ctrl.creer_tache(**dlg.resultat)
            self._rafraichir_liste()
            self._status(f"✅  Tâche « {t.titre} » ajoutée (id={t.id_tache}).")
        except (ValueError, StorageError) as e:
            mb.showerror("Erreur de saisie", str(e), parent=self)

    def _modifier(self) -> None:
        sel = self.tree.selection()
        if not sel:
            mb.showinfo("Sélection requise",
                        "Veuillez sélectionner une tâche à modifier.",
                        parent=self)
            return
        id_tache = int(sel[0])
        tache    = self.ctrl.obtenir_par_id(id_tache)
        if not tache:
            return

        dlg = DialogueTache(self, tache=tache)
        self.wait_window(dlg)
        if not dlg.resultat:
            return
        try:
            t = self.ctrl.modifier_tache(id_tache, **dlg.resultat)
            self._rafraichir_liste()
            self._status(f"✏️  Tâche « {t.titre} » modifiée.")
        except (ValueError, StorageError) as e:
            mb.showerror("Erreur de saisie", str(e), parent=self)

    def _supprimer(self) -> None:
        sel = self.tree.selection()
        if not sel:
            mb.showinfo("Sélection requise",
                        "Veuillez sélectionner une tâche à supprimer.",
                        parent=self)
            return
        id_tache = int(sel[0])
        tache    = self.ctrl.obtenir_par_id(id_tache)
        if not tache:
            return

        confirm = mb.askyesno(
            "Confirmer la suppression",
            f"Supprimer la tâche :\n«  {tache.titre}  »\n\nCette action est irréversible.",
            parent=self
        )
        if not confirm:
            return
        try:
            self.ctrl.supprimer_tache(id_tache)
            self._rafraichir_liste()
            self._status(f"🗑️  Tâche #{id_tache} supprimée.")
        except (ValueError, StorageError) as e:
            mb.showerror("Erreur", str(e), parent=self)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _exporter_rapport(self) -> None:
        try:
            chemin = self.ctrl.exporter_rapport()
            mb.showinfo(
                "Rapport exporté",
                f"Le rapport a été généré avec succès :\n{chemin}",
                parent=self
            )
            self._status(f"📤  Rapport exporté → {chemin}")
        except StorageError as e:
            mb.showerror("Erreur d'export", str(e), parent=self)

    # ------------------------------------------------------------------
    # Import fichier texte
    # ------------------------------------------------------------------

    def _importer_txt(self) -> None:
        """Ouvre un sélecteur de fichier et importe les tâches depuis un .txt."""
        import tkinter.filedialog as fd
        chemin = fd.askopenfilename(
            parent=self,
            title="Sélectionner le fichier texte à importer",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")],
        )
        if not chemin:
            return  # L'utilisateur a annulé

        try:
            rapport = self.ctrl.importer_depuis_txt(chemin)
        except StorageError as e:
            mb.showerror("Erreur d'import", str(e), parent=self)
            return

        nb_ok  = len(rapport["importees"])
        nb_ko  = len(rapport["ignorees"])
        total  = rapport["total_lues"]

        # Construire le message de résultat
        msg = (
            f"Import terminé.\n\n"
            f"  ✅  {nb_ok} tâche(s) importée(s) avec succès\n"
            f"  ⚠️  {nb_ko} ligne(s) ignorée(s) (invalides)\n"
            f"  📋  {total} ligne(s) de données lues au total"
        )
        if rapport["ignorees"]:
            details = "\n".join(
                f"  Ligne {num} : {raison}"
                for num, raison in rapport["ignorees"]
            )
            msg += f"\n\nDétail des lignes ignorées :\n{details}"

        mb.showinfo("Résultat de l'import", msg, parent=self)
        self._rafraichir_liste()
        self._status(f"📂  Import TXT : {nb_ok} tâche(s) ajoutée(s), {nb_ko} ignorée(s).")


    # ------------------------------------------------------------------
    # Tri
    # ------------------------------------------------------------------

    _tri_etat: dict = {}

    def _trier(self, colonne: str) -> None:
        """Tri croissant/décroissant par colonne."""
        items = [(self.tree.set(k, colonne), k)
                 for k in self.tree.get_children("")]
        inverse = self._tri_etat.get(colonne, False)
        items.sort(reverse=inverse)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
        self._tri_etat[colonne] = not inverse

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reinit_filtres(self) -> None:
        self.var_filtre_prio.set("Toutes")
        self.var_filtre_stat.set("Tous")
        self.var_urgentes.set(False)
        self.var_retard.set(False)
        self.var_recherche.set("")
        self._rafraichir_liste()
        self._status("Filtres réinitialisés.")

    def _status(self, message: str, erreur: bool = False) -> None:
        self.var_status.set(message)
