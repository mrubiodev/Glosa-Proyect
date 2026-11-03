from __future__ import annotations


class TemplateError(Exception):
    """Plantilla inválida. `problems` lista todos los errores encontrados."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("Plantilla inválida:\n- " + "\n- ".join(problems))
        self.problems = problems
