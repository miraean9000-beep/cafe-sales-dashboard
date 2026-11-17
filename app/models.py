from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class Sale(BaseModel):
    date: date
    value: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)
    memo: str = Field(default="", max_length=300)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Content


class Conversation(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def validate_order(self):
        for index, message in enumerate(self.messages):
            if message.role != ("user" if index % 2 == 0 else "assistant"):
                raise ValueError("메시지는 사용자와 답변 순서로 번갈아야 합니다.")
        return self


class Chat(Conversation):
    messages: list[Message] = Field(min_length=1, max_length=59)

    @model_validator(mode="after")
    def validate_last(self):
        if self.messages[-1].role != "user":
            raise ValueError("마지막 메시지는 사용자 질문이어야 합니다.")
        return self
