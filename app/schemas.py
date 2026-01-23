from pydantic import BaseModel
from enum import Enum
from typing import Optional

class LanguageCode(str, Enum):
    """Enum for supported language codes"""
    HINDI = "hi"
    TAMIL = "ta" 
    KANNADA = "kn"
    MALAYALAM = "ml"
    ENGLISH = "en"

class AgentName(str, Enum):
    NOT_GETTING_RIDES = "not_getting_rides"
    RIDE_RELATED_ISSUES = "ride_related_issues"
    RC_DL_ISSUES = "rc_dl_issues"

class DriverParams(BaseModel):
    language_code: Optional[LanguageCode] = None
    agent_name: Optional[AgentName] = None
    room_url: Optional[str] = None
    token: Optional[str] = None