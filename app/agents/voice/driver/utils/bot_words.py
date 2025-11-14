# Bot words/error messages for different languages
BOT_WORDS = {
    "ta": {
        "error_due_to_mcp_or_common": "மன்னிக்கவும், எங்கள் பக்கத்தில் சிறிது சிக்கல் ஏற்பட்டுள்ளது. தயவுசெய்து திரையில் காட்டப்பட்டுள்ள எண்ணைத் தொடர்பு கொள்ளவும்.",
        "driver_asked_to_call_agent": "நம்ம யாத்திரி டிரைவர் சப்போர்ட்டை அணுகியதற்கு நன்றி. தயவுசெய்து திரையில் தோன்றும் எண்ணைத் தொடர்பு கொள்ளவும்.",
        "time_out_error": "இடையூறுகளுக்காக மன்னிக்கவும். தயவுசெய்து திரையில் தோன்றும் எண்ணைத் தொடர்பு கொள்ளவும்.",
    },
    "kn": {
        "error_due_to_mcp_or_common": "ಕ್ಷಮಿಸಿ, ನಮ್ಮ ಕಡೆಯಿಂದ ಸ್ವಲ್ಪ ಸಮಸ್ಯೆ ಉಂಟಾಗಿದೆ. ದಯವಿಟ್ಟು ಪರದೆಯಲ್ಲಿ ತೋರಿಸಲಾದ ಸಂಖ್ಯೆಗೆ ಸಂಪರ್ಕಿಸಿ.",
        "driver_asked_to_call_agent": "ನಮ್ಮ ಯಾತ್ರಿ ಡ್ರೈವರ್ ಸಪೋರ್ಟ್‌ಗೆ ತಲುಪಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು. ದಯವಿಟ್ಟು ಪರದೆಯಲ್ಲಿ ತೋರಿಸುವ ಸಂಖ್ಯೆಗೆ ಸಂಪರ್ಕಿಸಿ.",
        "time_out_error": "ಅಸೌಕರ್ಯಕ್ಕಾಗಿ ಕ್ಷಮಿಸಿ. ದಯವಿಟ್ಟು ಪರದೆಯಲ್ಲಿ ತೋರಿಸುವ ಸಂಖ್ಯೆಗೆ ಸಂಪರ್ಕಿಸಿ.",
    },
    "hi": {
        "error_due_to_mcp_or_common": "क्षमा करें, हमारी तरफ से थोड़ी समस्या आ गई है। कृपया स्क्रीन पर दिए गए नंबर पर संपर्क करें।",
        "driver_asked_to_call_agent": "नम्मा यात्री ड्राइवर सपोर्ट से संपर्क करने के लिए धन्यवाद। कृपया स्क्रीन पर दिख रहे नंबर पर संपर्क करें।",
        "time_out_error": "असुविधा के लिए क्षमा करें। कृपया स्क्रीन पर दिख रहे नंबर पर संपर्क करें।",
    },
    "ml": {
        "error_due_to_mcp_or_common": "ക്ഷമിക്കണം, ഞങ്ങളുടെ വശത്ത് നിന്ന് കുറച്ച് പ്രശ്നം ഉണ്ടായി. ദയവായി സ്‌ക്രീനിൽ കാണിച്ചിരിക്കുന്ന നമ്പറിൽ ബന്ധപ്പെടുക.",
        "driver_asked_to_call_agent": "നമ്മ യാത്രി ഡ്രൈവർ സപ്പോർട്ടിലേക്ക് എത്തിയതിന് നന്ദി. ദയവായി സ്‌ക്രീനിൽ കാണിക്കുന്ന നമ്പറിൽ ബന്ധപ്പെടുക.",
        "time_out_error": "അസൗകര്യത്തിന് ക്ഷമിക്കണം. ദയവായി സ്‌ക്രീനിൽ കാണിക്കുന്ന നമ്പറിൽ ബന്ധപ്പെടുക.",
    },
}


def get_bot_words(language: str, key: str) -> str:
    """
    Get a specific bot word/error message for the specified language and key.
    
    Args:
        language: Language code (ta, kn, hi, ml).
        key: The key for the specific message (e.g., "error_due_to_mcp_or_common", "driver_asked_to_call_agent", "time_out_error").
    
    Returns:
        String message for the specified language and key.
    """
    language_dict = BOT_WORDS.get(language, BOT_WORDS["ta"])
    return language_dict.get(key, "")