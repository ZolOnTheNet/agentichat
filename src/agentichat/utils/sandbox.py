"""Sandbox de sécurité pour l'exécution des tools."""

import fnmatch
from pathlib import Path


class SandboxError(Exception):
    """Erreur de sécurité sandbox."""

    pass


class Sandbox:
    """Sandbox pour valider et restreindre l'accès aux fichiers."""

    def __init__(self, root: Path, config: dict | None = None) -> None:
        """Initialise le sandbox.

        Args:
            root: Répertoire racine du workspace (jail)
            config: Configuration du sandbox (max_file_size, blocked_paths, ignored_paths)
        """
        self.root = root.resolve()
        config = config or {}
        self.max_file_size = config.get("max_file_size", 1_000_000)
        self.blocked_patterns = config.get(
            "blocked_paths",
            [
                "**/.env",
                "**/*.key",
                "**/*.pem",
                "**/id_rsa",
                "**/credentials.json",
                "**/.ssh/*",
            ],
        )
        self.ignored_patterns = config.get(
            "ignored_paths",
            [
                "**/.venv/**", "**/venv/**", "**/env/**",
                "**/node_modules/**",
                "**/.git/**",
                "**/__pycache__/**",
                "**/build/**", "**/dist/**", "**/*.egg-info/**",
            ],
        )

    def validate_path(self, path: str) -> Path:
        """Valide et résout un chemin relatif.

        Args:
            path: Chemin relatif au workspace

        Returns:
            Chemin absolu validé

        Raises:
            SandboxError: Si le chemin est invalide ou bloqué
        """
        # Résoudre le chemin
        try:
            if Path(path).is_absolute():
                resolved = Path(path).resolve()
            else:
                resolved = (self.root / path).resolve()
        except Exception as e:
            raise SandboxError(f"Chemin invalide '{path}': {e}") from e

        # Vérifier qu'on reste dans le workspace (jail)
        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise SandboxError(
                f"Accès refusé : '{path}' sort du workspace. "
                f"Workspace: {self.root}"
            )

        # Vérifier les patterns bloqués
        for pattern in self.blocked_patterns:
            if resolved.match(pattern):
                raise SandboxError(
                    f"Accès refusé : '{path}' correspond au pattern bloqué '{pattern}'"
                )

        return resolved

    def validate_size(self, file_path: Path) -> None:
        """Vérifie qu'un fichier ne dépasse pas la taille maximale.

        Args:
            file_path: Chemin du fichier à vérifier

        Raises:
            SandboxError: Si le fichier est trop grand
        """
        if file_path.exists():
            size = file_path.stat().st_size
            if size > self.max_file_size:
                raise SandboxError(
                    f"Fichier trop grand : {size} octets "
                    f"(limite : {self.max_file_size})"
                )

    def is_readable(self, path: str) -> bool:
        """Vérifie si un chemin est lisible.

        Args:
            path: Chemin à vérifier

        Returns:
            True si le chemin est lisible
        """
        try:
            resolved = self.validate_path(path)
            return resolved.exists() and resolved.is_file()
        except SandboxError:
            return False

    def is_writable(self, path: str) -> bool:
        """Vérifie si un chemin est accessible en écriture.

        Args:
            path: Chemin à vérifier

        Returns:
            True si le chemin est accessible en écriture
        """
        try:
            resolved = self.validate_path(path)
            # Si le fichier existe, vérifier les permissions
            if resolved.exists():
                return resolved.is_file() and bool(resolved.stat().st_mode & 0o200)
            # Sinon, vérifier que le répertoire parent existe et est accessible
            else:
                return resolved.parent.exists() and resolved.parent.is_dir()
        except SandboxError:
            return False

    def should_ignore(self, path: Path) -> bool:
        """Vérifie si un chemin doit être ignoré lors des recherches récursives.

        Args:
            path: Chemin à vérifier (Path absolu ou relatif au workspace)

        Returns:
            True si le chemin correspond à un pattern ignoré
        """
        # Convertir en chemin relatif au workspace pour le matching
        try:
            if path.is_absolute():
                rel_path = path.relative_to(self.root)
            else:
                rel_path = path
        except ValueError:
            # Chemin hors du workspace, ne pas ignorer (sera bloqué par validate_path)
            return False

        # Convertir en string pour fnmatch
        rel_path_str = str(rel_path)

        # Vérifier les patterns ignorés
        for pattern in self.ignored_patterns:
            # Approche 1: fnmatch direct (pour patterns simples)
            if fnmatch.fnmatch(rel_path_str, pattern):
                return True

            # Approche 2: Vérifier si le pattern contient ** et l'adapter
            # Extraire le nom du répertoire à ignorer du pattern (ex: **/.venv/** → .venv)
            if "**" in pattern:
                # Pattern type: **/.venv/** ou **/node_modules/**
                parts = pattern.split("/")
                for part in parts:
                    if part and part != "**" and not part.startswith("*"):
                        # Vérifier si ce nom de répertoire apparaît dans le chemin
                        if part in rel_path.parts:
                            return True

        return False
