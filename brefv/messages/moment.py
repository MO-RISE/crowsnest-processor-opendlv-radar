# generated by datamodel-codegen:
#   filename:  moment.json
#   timestamp: 2023-04-28T09:01:10+00:00

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Moment(BaseModel):
    __root__: List[float] = Field(
        ...,
        description="Moment [Mx, My, Mz] (Nm) acting on a body and with respect to the body's BF frame of reference.",
        max_items=3,
        min_items=3,
        title='Moment',
    )
