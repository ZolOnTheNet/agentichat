"""Tool pour exécuter des commandes shell."""

import asyncio
from typing import Any

from ..utils.sandbox import Sandbox
from .registry import Tool


class ShellExecTool(Tool):
    """Tool pour exécuter une commande shell."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour définir le répertoire de travail
        """
        super().__init__(
            name="shell_exec",
            description=(
                "Exécute une commande shell. Utiliser pour git, npm, make, docker, "
                "tests, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Commande à exécuter",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Répertoire de travail (défaut: racine workspace)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout en secondes (défaut: 30)",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
            requires_confirmation=True,  # Confirmation requise
        )
        self.sandbox = sandbox

    async def execute(
        self, command: str, cwd: str | None = None, timeout: int = 30
    ) -> dict[str, Any]:
        """Exécute la commande shell.

        Args:
            command: Commande à exécuter
            cwd: Répertoire de travail
            timeout: Timeout en secondes

        Returns:
            Résultat de l'exécution
        """
        try:
            # Définir le répertoire de travail
            if cwd:
                work_dir = self.sandbox.validate_path(cwd)
                if not work_dir.is_dir():
                    return {"success": False, "error": f"'{cwd}' n'est pas un répertoire"}
            else:
                work_dir = self.sandbox.root

            # Exécuter la commande
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Timeout après {timeout}s",
                    "command": command,
                }

            # Décoder les sorties
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            return {
                "success": process.returncode == 0,
                "command": command,
                "returncode": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "command": command}
