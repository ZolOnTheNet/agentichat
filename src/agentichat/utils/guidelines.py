"""Gestionnaire de consignes utilisateur (AGENTICHAT.md → consignes.atc)."""

from pathlib import Path
from typing import Any

from ..backends.base import Backend, Message
from ..utils.logger import get_logger

logger = get_logger("agentichat.utils.guidelines")


class GuidelinesManager:
    """Gestionnaire des consignes utilisateur."""

    def __init__(self, workspace_dir: Path, backend: Backend | None = None) -> None:
        """Initialise le gestionnaire.

        Args:
            workspace_dir: Répertoire de travail (où chercher AGENTICHAT.md)
            backend: Backend LLM pour la compilation (optionnel)
        """
        self.workspace_dir = workspace_dir
        self.backend = backend
        self.source_file = workspace_dir / "AGENTICHAT.md"
        self.compiled_file = workspace_dir / ".agentichat" / "consignes.atc"

    def has_source(self) -> bool:
        """Vérifie si le fichier source existe.

        Returns:
            True si AGENTICHAT.md existe
        """
        return self.source_file.exists()

    def has_compiled(self) -> bool:
        """Vérifie si le fichier compilé existe.

        Returns:
            True si consignes.atc existe
        """
        return self.compiled_file.exists()

    def needs_compilation(self) -> bool:
        """Vérifie si une compilation est nécessaire.

        Returns:
            True si AGENTICHAT.md existe et est plus récent que consignes.atc
        """
        if not self.has_source():
            return False

        if not self.has_compiled():
            return True

        # Comparer les dates de modification
        source_mtime = self.source_file.stat().st_mtime
        compiled_mtime = self.compiled_file.stat().st_mtime

        return source_mtime > compiled_mtime

    def read_source(self) -> str:
        """Lit le contenu de AGENTICHAT.md.

        Returns:
            Contenu du fichier source

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
        """
        if not self.has_source():
            raise FileNotFoundError(f"Source file not found: {self.source_file}")

        return self.source_file.read_text(encoding="utf-8")

    def read_compiled(self) -> str:
        """Lit le contenu de consignes.atc.

        Returns:
            Contenu du fichier compilé

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
        """
        if not self.has_compiled():
            raise FileNotFoundError(f"Compiled file not found: {self.compiled_file}")

        return self.compiled_file.read_text(encoding="utf-8")

    def save_compiled(self, content: str) -> None:
        """Sauvegarde le contenu compilé dans consignes.atc.

        Args:
            content: Contenu à sauvegarder
        """
        # Créer le répertoire parent si nécessaire
        self.compiled_file.parent.mkdir(parents=True, exist_ok=True)

        self.compiled_file.write_text(content, encoding="utf-8")
        logger.info(f"Compiled guidelines saved to {self.compiled_file}")

    async def compile_guidelines(self, backend: Backend | None = None) -> str:
        """Compile les consignes avec le LLM.

        Lit AGENTICHAT.md, demande au LLM de l'optimiser pour format LLM,
        sauvegarde dans consignes.atc.

        Args:
            backend: Backend LLM à utiliser (ou self.backend si None)

        Returns:
            Contenu compilé

        Raises:
            ValueError: Si aucun backend n'est disponible
            FileNotFoundError: Si AGENTICHAT.md n'existe pas
        """
        llm = backend or self.backend
        if not llm:
            raise ValueError("No backend available for compilation")

        # Lire le fichier source
        source_content = self.read_source()

        # Créer le prompt de compilation
        compilation_prompt = f"""You are a technical assistant helping to optimize user guidelines for LLM consumption.

The user has written guidelines in a markdown file (AGENTICHAT.md). Your task is to:
1. Extract the key directives and rules
2. Reformat them in a concise, structured format optimized for LLM understanding
3. Use English for better LLM comprehension
4. Keep technical terms and specific instructions

Guidelines format:
- Start with "# PROJECT GUIDELINES"
- Use clear sections (## CODING STYLE, ## DOCUMENTATION, ## ARCHITECTURE, etc.)
- Use bullet points for rules
- Be concise but precise
- Include file references if mentioned

Here is the user's AGENTICHAT.md content:

---
{source_content}
---

Now generate the optimized guidelines (in English, structured, concise):"""

        # Demander au LLM de compiler
        logger.info("Compiling guidelines with LLM...")
        message = Message(role="user", content=compilation_prompt)
        response = await llm.chat(messages=[message], tools=None)

        compiled_content = response.content or ""

        if not compiled_content:
            raise ValueError("LLM returned empty content")

        # Sauvegarder
        self.save_compiled(compiled_content)

        return compiled_content

    def get_system_message(self) -> Message | None:
        """Retourne le message système avec les consignes.

        Returns:
            Message système avec les consignes, ou None si pas de consignes
        """
        if not self.has_compiled():
            return None

        try:
            compiled_content = self.read_compiled()
            return Message(
                role="system",
                content=f"[User Project Guidelines]\n\n{compiled_content}\n\n[End of Guidelines]"
            )
        except Exception as e:
            logger.error(f"Error reading compiled guidelines: {e}")
            return None

    def get_info(self) -> dict[str, Any]:
        """Retourne les informations sur les consignes.

        Returns:
            Dictionnaire avec les infos (exists, needs_compile, etc.)
        """
        return {
            "has_source": self.has_source(),
            "has_compiled": self.has_compiled(),
            "needs_compilation": self.needs_compilation(),
            "source_path": str(self.source_file),
            "compiled_path": str(self.compiled_file),
        }
