from typing import Protocol


class Confirmer(Protocol):
    def confirm(self, message: str) -> bool: ...


class PromptToolkitConfirmer:
    def confirm(self, message: str) -> bool:
        try:
            from prompt_toolkit import prompt
            answer = prompt(f"{message} (y/N): ")
            return answer.strip().lower() == "y"
        except (KeyboardInterrupt, EOFError):
            return False
