from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise ValueError("Question cannot be empty")
        return value

class Source(BaseModel):
    title: str
    url: str
    source_type: str
    published_or_updated: str | None = None

class Safety(BaseModel):
    level: str
    flags: list[str] = []
    disclaimer: str

class PurchaseLink(BaseModel):
    name: str
    url: str

class MedicationContext(BaseModel):
    name: str | None = None
    generic_name: str | None = None
    title: str | None = None
    label_set_id: str | None = None
    india_brand_name: str | None = None
    india_generic_name: str | None = None
    india_manufacturer: str | None = None
    india_strength: str | None = None
    india_form: str | None = None
    india_alternatives: list[str] = []
    purchase_links: list[PurchaseLink] = []

class ChatResponse(BaseModel):
    answer: str
    medication: MedicationContext
    safety: Safety
    sources: list[Source]
    grounded: bool
    provider: str
