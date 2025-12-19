"""Sandbox de sécurité pour l'exécution des tools."""

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
            config: Configuration du sandbox (max_file_size, blocked_paths)
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
                return resolved.is_file() and resolved.stat().st_mode & 0o200
            # Sinon, vérifier que le répertoire parent existe et est accessible
            else:
                return resolved.parent.exists() and resolved.parent.is_dir()
        except SandboxError:
            return False
