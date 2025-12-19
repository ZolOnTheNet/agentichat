"""Chargement de la configuration depuis YAML."""

import os
from pathlib import Path
from typing import Any

import yaml

from .schema import Config, validate_config


def load_config(config_path: Path | None = None) -> Config:
    """Charge la configuration depuis un fichier YAML.

    Ordre de priorité :
    1. config_path fourni explicitement
    2. .agentichat/config.yaml (workspace local)
    3. ~/.agentichat/config.yaml (global)
    4. Configuration par défaut

    Args:
        config_path: Chemin optionnel vers le fichier de config

    Returns:
        Configuration validée

    Raises:
        FileNotFoundError: Si le fichier spécifié n'existe pas
        ValueError: Si la configuration est invalide
    """
    # Chemins possibles
    paths_to_try: list[Path] = []

    if config_path:
        paths_to_try.append(config_path)
    else:
        # Workspace local
        cwd = Path.cwd()
        workspace_config = _find_workspace_config(cwd)
        if workspace_config:
            paths_to_try.append(workspace_config)

        # Config globale
        global_config = Path.home() / ".agentichat" / "config.yaml"
        paths_to_try.append(global_config)

    # Chercher le premier fichier existant
    config_data: dict[str, Any] = {}

    for path in paths_to_try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    config_data = loaded
                    break

    # Appliquer les variables d'environnement
    config_data = _apply_env_overrides(config_data)

    # Valider et retourner
    return validate_config(config_data)


def _find_workspace_config(start_path: Path) -> Path | None:
    """Recherche un fichier de config workspace en remontant l'arborescence.

    Cherche dans l'ordre :
    1. .agentichat/config.yaml
    2. .llm-context/config.yaml (legacy)

    Args:
        start_path: Répertoire de départ

    Returns:
        Chemin du fichier de config ou None
    """
    current = start_path.resolve()

    # Remonter jusqu'à la racine
    while True:
        for config_dir in [".agentichat", ".llm-context"]:
            config_file = current / config_dir / "config.yaml"
            if config_file.exists():
                return config_file

        # Arrêter à la racine
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Applique les overrides depuis les variables d'environnement.

    Variables supportées :
    - LLMCHAT_CONFIG: Chemin vers le fichier de config
    - LLMCHAT_DATA: Répertoire de données
    - LLMCHAT_PROXY_PORT: Port du proxy
    - LLMCHAT_LOG_LEVEL: Niveau de log
    - OLLAMA_HOST: URL du serveur Ollama
    - OPENAI_API_KEY: Clé API OpenAI
    - ANTHROPIC_API_KEY: Clé API Anthropic

    Args:
        config: Configuration à modifier

    Returns:
        Configuration avec les overrides appliqués
    """
    # Data dir
    if data_dir := os.getenv("LLMCHAT_DATA"):
        config["data_dir"] = data_dir

    # Proxy port
    if proxy_port := os.getenv("LLMCHAT_PROXY_PORT"):
        try:
            config["proxy_port"] = int(proxy_port)
        except ValueError:
            pass

    # Backend Ollama
    if ollama_host := os.getenv("OLLAMA_HOST"):
        if "backends" not in config:
            config["backends"] = {}
        if "ollama" not in config["backends"]:
            config["backends"]["ollama"] = {}
        config["backends"]["ollama"]["url"] = ollama_host

    # API Keys
    if openai_key := os.getenv("OPENAI_API_KEY"):
        if "backends" not in config:
            config["backends"] = {}
        if "openai" in config["backends"]:
            config["backends"]["openai"]["api_key"] = openai_key

    if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
        if "backends" not in config:
            config["backends"] = {}
        if "anthropic" in config["backends"]:
            config["backends"]["anthropic"]["api_key"] = anthropic_key

    return config


def get_config_path() -> Path:
    """Retourne le chemin du fichier de configuration à utiliser.

    Ordre de priorité :
    1. .agentichat/config.yaml (workspace local)
    2. ~/.agentichat/config.yaml (global)

    Returns:
        Chemin du fichier de config (peut ne pas exister)
    """
    # Workspace local
    cwd = Path.cwd()
    workspace_config = _find_workspace_config(cwd)
    if workspace_config:
        return workspace_config

    # Config globale
    return Path.home() / ".agentichat" / "config.yaml"


def save_config(config: Config, config_path: Path | None = None) -> None:
    """Sauvegarde la configuration dans un fichier YAML.

    Args:
        config: Configuration à sauvegarder
        config_path: Chemin du fichier de destination (par défaut: config actuelle)
    """
    # Utiliser le chemin par défaut si non fourni
    if config_path is None:
        config_path = get_config_path()

    # Créer le répertoire parent si nécessaire
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convertir en dict
    config_dict = {
        "default_backend": config.default_backend,
        "backends": {
            name: {
                "type": backend.type,
                "url": backend.url,
                "model": backend.model,
                "timeout": backend.timeout,
                "max_tokens": backend.max_tokens,
                "temperature": backend.temperature,
                **({"api_key": backend.api_key} if backend.api_key else {}),
            }
            for name, backend in config.backends.items()
        },
        "sandbox": {
            "max_file_size": config.sandbox.max_file_size,
            "blocked_paths": config.sandbox.blocked_paths,
            **(
                {"allowed_commands": config.sandbox.allowed_commands}
                if config.sandbox.allowed_commands
                else {}
            ),
        },
        "confirmations": {
            "text_operations": config.confirmations.text_operations,
            "shell_commands": config.confirmations.shell_commands,
        },
        "data_dir": str(config.data_dir),
        "max_iterations": config.max_iterations,
        "proxy_port": config.proxy_port,
        "proxy_host": config.proxy_host,
    }

    # Écrire le fichier
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
