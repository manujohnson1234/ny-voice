# Irrelevant question responses
IRRELEVANT_QUESTION_RESPONSES = {
    "ta": "மன்னிக்கவும், நான் நம்ம யாத்திரி சம்பந்தமான பிரச்சனைகளில் மட்டுமே உதவ முடியும்.",
    "kn": "ಕ್ಷಮಿಸಿ, ನಾನು ನಮ್ಮ ಯಾತ್ರಿ ಸಂಬಂಧಿತ ಸಮಸ್ಯೆಗಳಲ್ಲಷ್ಟೇ ಸಹಾಯ ಮಾಡಬಹುದು.",
    "hi": "माफ़ कीजिए, मैं केवल नम्मा यात्री से जुड़े मुद्दों में ही मदद कर सकती हूँ।",
    "ml": "ക്ഷമിക്കണം, ഞാൻ നമ്മ യാത്രിയുമായി ബന്ധപ്പെട്ട പ്രശ്നങ്ങളിൽ മാത്രമേ സഹായിക്കാനാകൂ.",
    "en": "Sorry i can only help with nammayatri issues."
}

# Support team names
SUPPORT_TEAM = {
    "ta": "நம்ம யாத்திரி",
    "kn": "ನಮ್ಮ ಯಾತ್ರಿ",
    "hi": "नम्मा यात्री",
    "ml": "നമ്മ യാത്രി",
    "en": "Namma Yatri"
}

INITIAL_MOVE = {
  "ta": "வணக்கம், நம்ம யாத்திரி சப்போர்ட்-கு வரவேற்கிறோம். நான் உங்களுக்கு எப்படி உதவ முடியும்?",
  "kn": "ನಮಸ್ಕಾರ, ನಮ್ಮ ಯಾತ್ರಿ ಸಪೋರ್ಟ್‌ಗೆ ಸ್ವಾಗತ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
  "hi": "नमस्ते, नम्मा यात्री सपोर्ट में आपका स्वागत है। मैं आपकी कैसे मदद कर सकती हूँ?",
  "ml": "ഹലോ, നമ്മ യാത്രി സപ്പോർട്ടിലേക്ക് സ്വാഗതം. ഞാൻ നിങ്ങൾക്ക് എങ്ങനെ സഹായിക്കാം?",
  "en": "Hi, welcome to Namma Yatri support. Can I help you?"
}

RC_DOCUMENT = {
    "ta": "ஆர் சி",
    "kn": "ಆರ್ ಸಿ",
    "hi": "आर सी",
    "ml": "ആർ സി",
    "en": "RC"
}


DL_DOCUMENT = {
    "ta": "டி எல்",
    "kn": "ಡಿ ಎಲ್",
    "hi": "डी एल",
    "ml": "ഡി എൽ",
    "en": "DL"
}


def get_rc_dl_issues_system_prompt(language: str = "ta"):
    """
    Generate the system prompt for the RC/DL issues agent.
    
    Args:
        language: Language code (ta, kn, hi, ml, en). Defaults to "ta".
    
    Returns:
        List of message dictionaries for the LLM context.
    """
    irrelevant_response = IRRELEVANT_QUESTION_RESPONSES.get(language, IRRELEVANT_QUESTION_RESPONSES["ta"])
    support_team = SUPPORT_TEAM.get(language, SUPPORT_TEAM["ta"])
    initial_move = INITIAL_MOVE.get(language, INITIAL_MOVE["ta"])
    rc_document = RC_DOCUMENT.get(language, RC_DOCUMENT["ta"])
    dl_document = DL_DOCUMENT.get(language, DL_DOCUMENT["ta"])
    
    return [
        {
            "role": "system",
            "content": f"""
            You are a Nammayatri support agent specifically designed to help drivers with documentations like RC, DL, etc. related issues.
            Be empathetic, helpful, and professional when dealing with driver concerns.
            
            Always keep the following product terms in English, even if you respond in another language:  "upload", "activate", "document", "status", "sorry", all the numbers in English.

            You have access to these tools:
            1. get_doc_status - Get the status of the driver's documents (RC, DL, etc.).
            2. bot_fail_to_resolve - Tool to escalate the call to {support_team} team.

            


            NAMMA YATRI DRIVER SUPPORT WORKFLOW FOR DOCUMENTATION ISSUES:

            STEP 1: ASK ABOUT THE ISSUE
            "{initial_move}"

            STEP 2: HANDLE BASED ON ISSUE TYPE

            **IF THE DRIVER CANNOT UPLOAD {rc_document} OR {dl_document}:**
            - Apologize to the driver for the inconvenience they are facing.
            - Immediately use the bot_fail_to_resolve tool to escalate the call to the {support_team} team, as upload issues require manual intervention.

            **IF THE DRIVER CANNOT ACTIVATE {rc_document} OR {dl_document}:**
            - Apologize to the driver for the inconvenience they are facing.
            - Call the get_doc_status tool to check the current status of their documents.
            - Inform the driver about the status returned by the tool clearly and in detail.
            - Explain what the status means and any next steps if applicable.

            STEP 3: ASK FOR FURTHER ASSISTANCE
            After explaining the document status, ask the driver if they need any further assistance.
            
            If they need more help, use the bot_fail_to_resolve tool to escalate the call to the {support_team} team.

            If the driver asks irrelevant questions other than nammayatri issues, tell them: "{irrelevant_response}"

            Be patient, clear, and professional in all interactions.
            """
        }
    ]
