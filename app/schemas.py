from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Choice = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class QuestionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")  # extra fields are allowed but ignored

    text: str = Field(min_length=1, max_length=500)
    type: Literal["multiple_choice", "true_false"]
    choices: list[Choice]
    correct_index: int
    time_limit_sec: int = Field(default=20, ge=5, le=60)

    @model_validator(mode="after")
    def check_choices(self):
        n = len(self.choices)
        if self.type == "multiple_choice" and not 2 <= n <= 4:
            raise ValueError("multiple_choice needs 2 to 4 choices")
        if self.type == "true_false" and n != 2:
            raise ValueError("true_false needs exactly 2 choices")
        if not 0 <= self.correct_index < n:
            raise ValueError("correct_index must point to one of the choices")
        return self


class QuestionSetIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=3, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=50)
    grade_level: str | None = Field(default=None, max_length=50)
    questions: list[QuestionIn] = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class SessionCreate(BaseModel):
    question_set_id: int
    duration_sec: int = Field(default=300, ge=30, le=3600)
    starting_lives: int = Field(default=3, ge=1, le=10)


class SessionPatch(BaseModel):
    status: Literal["playing", "ended"]


class JoinRequest(BaseModel):
    nickname: str

    @field_validator("nickname")
    @classmethod
    def check_nickname(cls, v: str) -> str:
        v = v.strip()
        if not 2 <= len(v) <= 20:
            raise ValueError("nickname must be 2 to 20 characters")
        return v


class AnswerRequest(BaseModel):
    question_id: int
    choice_index: int = Field(ge=0, le=3)


class ChestRequest(BaseModel):
    chest_offer_id: int
    slot_number: int = Field(ge=1, le=3)
