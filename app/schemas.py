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

class DriverParams(BaseModel):
    phoneNumber: str
    current_version_of_app: Optional[str] = None
    latest_version_of_app: Optional[str] = None
    language_code: Optional[LanguageCode] = None