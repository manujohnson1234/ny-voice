# Bot words/error messages for different languages
BOT_WORDS = {
    "ta": {
        "error_due_to_mcp_or_common": "sorry, எங்கள் பக்கத்தில் சிறிது சிக்கல் ஏற்பட்டுள்ளது. தயவுசெய்து  screen-la இருக்கும் number-க்கு call பண்ணுங்க.",
        "driver_asked_to_call_agent": "இந்த issue தீர்க்க, தயவுசெய்து மொபைல்ல காமிக்குற நம்பருக்கு call பண்ணுங்க.",
        "time_out_error": "நா மூனு நிமிஷத்துக்கு மேல help பண்ண முடியாது, சோரி. இன்னும் help வேணும்னா, screen-la இருக்கும் number-க்கு call பண்ணுங்க.",
    },
    "kn": {
        "error_due_to_mcp_or_common": "sorry, ನಮ್ಮ side ಸ್ವಲ್ಪ issue ಆಗಿದೆ. ದಯವಿಟ್ಟು screen ಮೇಲೆ ಇರುವ numberಗೆ call ಮಾಡಿ.",
        "driver_asked_to_call_agent": "ಈ issue solve ಮಾಡಲು, ದಯವಿಟ್ಟು mobile ನಲ್ಲಿ ಕಾಣ್ತಿರುವ number ಗೆ call ಮಾಡಿ.",
        "time_out_error": "ನಾ ಮೂರು ನಿಮಿಷಕ್ಕಿಂತ ಹೆಚ್ಚು help ಮಾಡೋಕಾಗಲ್ಲ, sorry. ಇನ್ನೂ help ಬೇಕಂದ್ರೆ, screen ನಲ್ಲಿ ಇರೋ number ಗೆ call ಮಾಡಿ.",
    },
    "hi": {
        "error_due_to_mcp_or_common": "sorry, हमारी side थोड़ा issue हो गया है. कृपया screen पर दिख रहे number पर call करें.",
        "driver_asked_to_call_agent": "इस issue को solve करने के लिए, कृपया mobile पर दिख रहे number पर call करें.",
        "time_out_error": "मैं तीन मिनट से ज़्यादा help नहीं कर सकता, sorry. अगर और help चाहिए तो screen पर दिख रहे number पर call करें.",
    },
    "ml": {
        "error_due_to_mcp_or_common": "ക്ഷമിക്കണം, ഞങ്ങളുടെ വശത്ത് നിന്ന് കുറച്ച് പ്രശ്നം ഉണ്ടായി. ദയവായി സ്‌ക്രീനിൽ കാണിച്ചിരിക്കുന്ന നമ്പറിൽ ബന്ധപ്പെടുക.",
        "driver_asked_to_call_agent": "നമ്മ യാത്രി ഡ്രൈവർ സപ്പോർട്ടിലേക്ക് എത്തിയതിന് നന്ദി. ദയവായി സ്‌ക്രീനിൽ കാണിക്കുന്ന നമ്പറിൽ ബന്ധപ്പെടുക.",
        "time_out_error": "അസൗകര്യത്തിന് ക്ഷമിക്കണം. ദയവായി സ്‌ക്രീനിൽ കാണിക്കുന്ന നമ്പറിൽ ബന്ധപ്പെടുക.",
    },
    "en": {
        "error_due_to_mcp_or_common": "Sorry, there is a small issue on our side. Please contact the number shown on the screen.",
        "driver_asked_to_call_agent": "Thank you for contacting Namma Yatri Driver Support. Please contact the number shown on the screen.",
        "time_out_error": "Sorry, there is a small issue on our side. Please contact the number shown on the screen.",
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
    language_dict = BOT_WORDS.get(language, BOT_WORDS["kn"])
    return language_dict.get(key, "")