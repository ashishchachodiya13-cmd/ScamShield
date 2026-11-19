from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class RedFlagDefinition(BaseModel):
    id: str
    name_en: str
    name_hi: str
    description_en: str
    description_hi: str
    weight: int = Field(ge=1, le=10)
    patterns: List[str]


class ScoringThresholds(BaseModel):
    low_max: int = 2
    medium_max: int = 5


class CategoryDefinition(BaseModel):
    id: str
    name_en: str
    name_hi: str
    associated_flags: List[str]
    pretext_keywords: List[str] = Field(default_factory=list)


class RedFlagsConfig(BaseModel):
    flags: List[RedFlagDefinition]
    thresholds: ScoringThresholds = Field(default_factory=ScoringThresholds)
    categories: List[CategoryDefinition]


class MatchedFlag(BaseModel):
    id: str
    name_en: str
    name_hi: str
    weight: int
    snippets: List[str]


class ActionItem(BaseModel):
    dos: List[str]
    donts: List[str]
    official_channels: List[str]


class ActionsConfig(BaseModel):
    general: ActionItem
    categories: Dict[str, ActionItem]


class TemplateExplanation(BaseModel):
    en: str
    hi: str


class TemplatesConfig(BaseModel):
    categories: Dict[str, TemplateExplanation]
    zero_flags: TemplateExplanation


class AnalysisRequest(BaseModel):
    text: str = Field(min_length=1, description="Message or transcript text to analyze")
    language: Literal["en", "hi"] = "en"


class AnalysisResponse(BaseModel):
    risk_level: Literal["Low", "Medium", "High"]
    score: int
    category: str
    category_name: str
    matched_flags: List[MatchedFlag]
    explanation: str
    explanation_source: Literal["llm", "template"]
    actions: ActionItem
    language: Literal["en", "hi"]
    masked_text: str


class OCRResponse(BaseModel):
    extracted_text: str
    success: bool
    message: str


class FeedbackRequest(BaseModel):
    helpful: bool
    category: Optional[str] = None
    risk_level: Optional[str] = None
    comment: Optional[str] = None
