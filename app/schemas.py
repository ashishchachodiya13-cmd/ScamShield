from typing import List, Dict, Optional, Literal, Any
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
    source: Literal["text", "screenshot", "share"] = "text"


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
    analysis_id: Optional[int] = None


class OCRResponse(BaseModel):
    extracted_text: str
    success: bool
    message: str


class FeedbackRequest(BaseModel):
    helpful: bool
    category: Optional[str] = None
    risk_level: Optional[str] = None
    comment: Optional[str] = None
    analysis_id: Optional[int] = None


# ==============================================================================
# Auth & User Schemas (Stage 1)
# ==============================================================================

class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: str
    last_login_at: Optional[str] = None


class PreferencesResponse(BaseModel):
    language: str = "en"
    large_text: bool = False
    retain_masked_text: bool = False
    notify_settings: Dict[str, Any] = Field(default_factory=dict)


class UserMeResponse(BaseModel):
    user: UserResponse
    preferences: PreferencesResponse


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    current_password: Optional[str] = Field(default=None, min_length=1)
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class AuthMessageResponse(BaseModel):
    status: str = "ok"
    message: str


# ==============================================================================
# History, Stats, Reports & Preferences Schemas (Stage 2)
# ==============================================================================

class HistoryItemResponse(BaseModel):
    id: int
    created_at: str
    risk_level: str
    score: int
    category: str
    category_name: str
    flag_ids: List[str]
    flag_count: int
    language: str
    source: str
    has_masked_text: bool


class HistoryListResponse(BaseModel):
    items: List[HistoryItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class HistoryDetailResponse(BaseModel):
    id: int
    created_at: str
    risk_level: str
    score: int
    category: str
    category_name: str
    matched_flags: List[MatchedFlag]
    explanation: str
    actions: ActionItem
    language: str
    source: str
    masked_text: Optional[str] = None
    retained_label: str


class StatsOverviewResponse(BaseModel):
    total_scans: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    recent_scans: List[Dict[str, Any]]
    recent_high_risk: List[Dict[str, Any]]
    category_distribution: List[Dict[str, Any]]
    risk_distribution: List[Dict[str, Any]]


class CategoryBreakdownItem(BaseModel):
    category: str
    count: int
    percentage: float


class TimelineItem(BaseModel):
    date: str
    total: int
    high: int
    medium: int
    low: int


class ReportsResponse(BaseModel):
    range: str
    total_scans: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    high_risk_percentage: float
    category_breakdown: List[CategoryBreakdownItem]
    activity_timeline: List[TimelineItem]


class PreferencesUpdateRequest(BaseModel):
    language: Optional[Literal["en", "hi"]] = None
    large_text: Optional[bool] = None
    retain_masked_text: Optional[bool] = None
    notify_settings: Optional[Dict[str, Any]] = None
