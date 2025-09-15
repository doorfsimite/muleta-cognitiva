from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str = Field(..., description="Nome canônico curto e claro")
    type: str = Field(..., description="Tipo da entidade, e.g., conceito, pessoa")
    description: str = Field(
        ..., description="Resumo objetivo em PT-BR com até 25 palavras"
    )


class Relation(BaseModel):
    from_: str = Field(
        ..., alias="from", description="Nome canônico da entidade origem"
    )
    to: str = Field(..., description="Nome canônico da entidade destino")
    type: str = Field(..., description="Tipo da relação, e.g., parte_de, relacionado_a")
    evidence: str = Field(
        ..., description="Citação curta do texto ou explicação objetiva"
    )


class ContentAnalysis(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)
