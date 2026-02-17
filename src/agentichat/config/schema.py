"""Schéma et validation de la configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BackendConfig:
    """Configuration d'un backend LLM."""

    type: str  # "ollama", "vllm", "openai"
    url: str
    model: str
    timeout: int = 30
    max_tokens: int = 4096
    temperature: float = 0.7
    api_key: str | None = None
    max_parallel_tools: int | None = None  # None = illimité, 1 = un seul à la fois


@dataclass
class SandboxConfig:
    """Configuration du sandbox de sécurité."""

    max_file_size: int = 1_000_000  # 1 MB
    blocked_paths: list[str] = field(
        default_factory=lambda: [
            "**/.env",
            "**/*.key",
            "**/*.pem",
            "**/id_rsa",
            "**/credentials.json",
        ]
    )
    ignored_paths: list[str] = field(
        default_factory=lambda: [
            # Environnements virtuels Python
            "**/.venv/**",
            "**/venv/**",
            "**/env/**",
            "**/.virtualenv/**",
            # Dépendances Node.js
            "**/node_modules/**",
            # Contrôle de version
            "**/.git/**",
            # Caches Python
            "**/__pycache__/**",
            "**/.pytest_cache/**",
            "**/.mypy_cache/**",
            "**/.ruff_cache/**",
            # Build artifacts
            "**/build/**",
            "**/dist/**",
            "**/*.egg-info/**",
            # IDEs
            "**/.vscode/**",
            "**/.idea/**",
            # Autres
            "**/.DS_Store",
        ]
    )
    allowed_commands: list[str] | None = None  # None = tout autorisé


@dataclass
class ConfirmationConfig:
    """Configuration des confirmations utilisateur."""

    text_operations: bool = True  # Confirmer write_file, delete_file
    shell_commands: bool = True  # Confirmer shell_exec


@dataclass
class CompressionConfig:
    """Configuration de la compression de conversation."""

    auto_enabled: bool = False  # Activer la compression automatique
    auto_threshold: int = 20  # Nombre de messages pour déclencher auto-compress
    auto_keep: int = 5  # Nombre de messages à garder après auto-compress
    warning_threshold: float = 0.75  # Pourcentage (0-1) pour afficher avertissement
    max_messages: int | None = None  # Limite max de messages (None = illimité)


@dataclass
class GuidelinesConfig:
    """Configuration du chargement des guidelines (AGENTICHAT.md)."""

    # Mode de chargement: "confirm" (demander), "auto" (automatique), "off" (jamais)
    load_mode: str = "confirm"


@dataclass
class Config:
    """Configuration globale de agentichat."""

    # Backend par défaut
    default_backend: str = "ollama"
    backends: dict[str, BackendConfig] = field(default_factory=dict)

    # Sandbox
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)

    # Confirmations
    confirmations: ConfirmationConfig = field(default_factory=ConfirmationConfig)

    # Compression
    compression: CompressionConfig = field(default_factory=CompressionConfig)

    # Guidelines
    guidelines: GuidelinesConfig = field(default_factory=GuidelinesConfig)

    # Chemins
    config_dir: Path = field(default_factory=lambda: Path.home() / ".agentichat")  # Config globale
    data_dir: Path = field(default_factory=lambda: Path.cwd() / ".agentichat")  # Données locales

    # Agent
    max_iterations: int = 10

    # Proxy daemon
    proxy_port: int = 5157
    proxy_host: str = "127.0.0.1"


def validate_config(config: dict[str, Any]) -> Config:
    """Valide et convertit un dict en objet Config.

    Args:
        config: Configuration brute issue du YAML

    Returns:
        Config validée

    Raises:
        ValueError: Si la configuration est invalide
    """
    # Backend par défaut
    default_backend = config.get("default_backend", "ollama")

    # Backends
    backends_dict = {}
    for name, backend_data in config.get("backends", {}).items():
        if not isinstance(backend_data, dict):
            raise ValueError(f"Backend '{name}' doit être un objet")

        required_fields = ["type", "url", "model"]
        for field_name in required_fields:
            if field_name not in backend_data:
                raise ValueError(f"Backend '{name}' manque le champ '{field_name}'")

        backends_dict[name] = BackendConfig(
            type=backend_data["type"],
            url=backend_data["url"],
            model=backend_data["model"],
            timeout=backend_data.get("timeout", 30),
            max_tokens=backend_data.get("max_tokens", 4096),
            temperature=backend_data.get("temperature", 0.7),
            api_key=backend_data.get("api_key"),
            max_parallel_tools=backend_data.get("max_parallel_tools"),
        )

    # Vérifier que le backend par défaut existe
    if default_backend not in backends_dict and backends_dict:
        raise ValueError(
            f"default_backend '{default_backend}' n'existe pas dans backends"
        )

    # Sandbox
    sandbox_data = config.get("sandbox", {})
    sandbox = SandboxConfig(
        max_file_size=sandbox_data.get("max_file_size", 1_000_000),
        blocked_paths=sandbox_data.get(
            "blocked_paths",
            [
                "**/.env",
                "**/*.key",
                "**/*.pem",
                "**/id_rsa",
                "**/credentials.json",
            ],
        ),
        ignored_paths=sandbox_data.get(
            "ignored_paths",
            [
                "**/.venv/**", "**/venv/**", "**/env/**", "**/.virtualenv/**",
                "**/node_modules/**",
                "**/.git/**",
                "**/__pycache__/**", "**/.pytest_cache/**", "**/.mypy_cache/**", "**/.ruff_cache/**",
                "**/build/**", "**/dist/**", "**/*.egg-info/**",
                "**/.vscode/**", "**/.idea/**",
                "**/.DS_Store",
            ],
        ),
        allowed_commands=sandbox_data.get("allowed_commands"),
    )

    # Confirmations
    confirm_data = config.get("confirmations", {})
    confirmations = ConfirmationConfig(
        text_operations=confirm_data.get("text_operations", True),
        shell_commands=confirm_data.get("shell_commands", True),
    )

    # Compression
    compress_data = config.get("compression", {})
    compression = CompressionConfig(
        auto_enabled=compress_data.get("auto_enabled", False),
        auto_threshold=compress_data.get("auto_threshold", 20),
        auto_keep=compress_data.get("auto_keep", 5),
        warning_threshold=compress_data.get("warning_threshold", 0.75),
        max_messages=compress_data.get("max_messages"),
    )

    # Guidelines
    guidelines_data = config.get("guidelines", {})
    load_mode = guidelines_data.get("load_mode", "confirm")
    if load_mode not in ["confirm", "auto", "off"]:
        raise ValueError(f"guidelines.load_mode doit être 'confirm', 'auto' ou 'off', pas '{load_mode}'")
    guidelines = GuidelinesConfig(load_mode=load_mode)

    # Chemins
    config_dir = Path.home() / ".agentichat"  # Config globale (non configurable)

    data_dir_str = config.get("data_dir")
    if data_dir_str:
        data_dir = Path(data_dir_str).expanduser()
    else:
        data_dir = Path.cwd() / ".agentichat"  # Données locales au projet

    # Agent
    max_iterations = config.get("max_iterations", 10)

    # Proxy
    proxy_port = config.get("proxy_port", 5157)
    proxy_host = config.get("proxy_host", "127.0.0.1")

    return Config(
        default_backend=default_backend,
        backends=backends_dict,
        sandbox=sandbox,
        confirmations=confirmations,
        compression=compression,
        guidelines=guidelines,
        config_dir=config_dir,
        data_dir=data_dir,
        max_iterations=max_iterations,
        proxy_port=proxy_port,
        proxy_host=proxy_host,
    )
