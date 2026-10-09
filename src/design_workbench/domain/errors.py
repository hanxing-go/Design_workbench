from dataclasses import dataclass


@dataclass(eq=False)
class WorkbenchError(Exception):
    code: str
    message: str
    location: str = ""
    revision: int | None = None

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "revision": self.revision,
        }
