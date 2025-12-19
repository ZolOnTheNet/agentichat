"""Gestionnaire d'affichage et de recherche dans les logs."""

from pathlib import Path


class LogViewer:
    """Gestionnaire pour visualiser et rechercher dans les logs.

    Fonctionnalités:
    - show: Affiche les nouveaux logs depuis le dernier appel
    - fullshow: Affiche tous les logs depuis le dernier clear
    - clear: Marque un point de départ pour fullshow
    - search: Recherche un texte dans les logs avec contexte
    - config: Configure les paramètres d'affichage
    - status: Affiche les statistiques
    """

    def __init__(self, log_file: Path) -> None:
        """Initialise le visualiseur de logs.

        Args:
            log_file: Chemin vers le fichier de log
        """
        self.log_file = log_file
        self.last_read_position = 0  # Position du dernier show
        self.clear_position = 0  # Position du dernier clear

        # Configuration par défaut
        self.config_show_lines = 20  # Nombre de lignes pour show
        self.config_search_before = 3  # Lignes avant le match
        self.config_search_after = 10  # Lignes après le match

    def show(self) -> list[str]:
        """Affiche les nouveaux logs depuis le dernier appel.

        Returns:
            Liste des lignes de log nouvelles
        """
        if not self.log_file.exists():
            return []

        with open(self.log_file, 'r') as f:
            # Aller à la dernière position lue
            f.seek(self.last_read_position)
            lines = f.readlines()
            # Mettre à jour la position
            self.last_read_position = f.tell()

        # Limiter au nombre configuré
        if len(lines) > self.config_show_lines:
            lines = lines[-self.config_show_lines:]

        return [line.rstrip() for line in lines]

    def fullshow(self) -> list[str]:
        """Affiche tous les logs depuis le dernier clear ou le début.

        Returns:
            Liste de toutes les lignes depuis le clear
        """
        if not self.log_file.exists():
            return []

        with open(self.log_file, 'r') as f:
            # Aller à la position du clear
            f.seek(self.clear_position)
            lines = f.readlines()
            # Mettre à jour la position de lecture
            self.last_read_position = f.tell()

        return [line.rstrip() for line in lines]

    def clear(self) -> None:
        """Marque la position actuelle comme nouveau point de départ."""
        if not self.log_file.exists():
            # Créer le fichier s'il n'existe pas
            self.log_file.touch()

        # Marquer la position actuelle comme point de clear
        with open(self.log_file, 'r') as f:
            f.seek(0, 2)  # Aller à la fin
            self.clear_position = f.tell()
            self.last_read_position = f.tell()

    def search(self, query: str) -> list[tuple[int, list[str]]]:
        """Recherche un texte dans les logs avec contexte.

        Args:
            query: Texte à rechercher

        Returns:
            Liste de tuples (numéro_ligne, [lignes_avec_contexte])
        """
        if not self.log_file.exists():
            return []

        with open(self.log_file, 'r') as f:
            all_lines = f.readlines()

        # Trouver toutes les occurrences
        matches = []
        for i, line in enumerate(all_lines):
            if query.lower() in line.lower():
                # Extraire le contexte
                start = max(0, i - self.config_search_before)
                end = min(len(all_lines), i + self.config_search_after + 1)
                context_lines = [l.rstrip() for l in all_lines[start:end]]
                matches.append((i + 1, context_lines))  # Numéro de ligne (1-indexed)

        # Mettre à jour la position de lecture
        self.last_read_position = sum(len(line) for line in all_lines)

        return matches

    def set_config_show(self, num_lines: int) -> None:
        """Configure le nombre de lignes pour show.

        Args:
            num_lines: Nombre de lignes à afficher
        """
        if num_lines > 0:
            self.config_show_lines = num_lines

    def set_config_search(self, before: int, after: int) -> None:
        """Configure le contexte pour search.

        Args:
            before: Nombre de lignes avant le match
            after: Nombre de lignes après le match
        """
        if before >= 0:
            self.config_search_before = before
        if after >= 0:
            self.config_search_after = after

    def get_status(self) -> dict[str, int | str]:
        """Obtient les statistiques des logs.

        Returns:
            Dictionnaire avec les statistiques
        """
        if not self.log_file.exists():
            return {
                "total_lines": 0,
                "total_size": 0,
                "show_lines_config": self.config_show_lines,
                "search_before_config": self.config_search_before,
                "search_after_config": self.config_search_after,
                "last_read_position": 0,
                "clear_position": 0,
            }

        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            total_lines = len(lines)
            f.seek(0, 2)
            total_size = f.tell()

        return {
            "total_lines": total_lines,
            "total_size": total_size,
            "show_lines_config": self.config_show_lines,
            "search_before_config": self.config_search_before,
            "search_after_config": self.config_search_after,
            "last_read_position": self.last_read_position,
            "clear_position": self.clear_position,
        }
