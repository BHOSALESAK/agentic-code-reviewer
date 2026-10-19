from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class PreviewRequest(BaseModel):
    fixture_id: str | None = None
    reference: str | None = None

    @model_validator(mode="after")
    def require_one_source(self) -> "PreviewRequest":
        if bool(self.fixture_id) == bool(self.reference):
            raise ValueError("provide exactly one fixture_id or reference")
        return self


class FixtureSummary(BaseModel):
    fixture_id: str
    title: str
    number: Annotated[int, Field(ge=1)]
    repository: str
    changed_files: int
    synthetic: bool = True
