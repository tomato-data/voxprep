from typing import Protocol


class TextEditor(Protocol):
    def edit(self, initial: str) -> str | None: ...


class PromptToolkitTextEditor:
    def edit(self, initial: str) -> str | None:
        try:
            from prompt_toolkit import prompt
            return prompt("Edit text: ", default=initial)
        except (KeyboardInterrupt, EOFError):
            return None
