RIDE_RELATED_ISSUE = {
    "ta": "உங்களுக்கு உதவ, தயவுசெய்து இந்த call-ஐ end பண்ணி, app-ல பிரச்சனை இருக்குற ride-ஐ select பண்ணுங்க.",
    "kn":"ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು, ದಯವಿಟ್ಟು ಈ ಕಾಲ್ ಎಂಡ್ ಮಾಡಿ, ಆಪ್‌ನಲ್ಲಿ ಸಮಸ್ಯೆ ಇರುವ ರೈಡ್ ಅನ್ನು ಸೆಲೆಕ್ಟ್ ಮಾಡಿ.",
    "ml":"നിങ്ങളെ സഹായിക്കാൻ, ദയവായി ഈ കോൾ എണ്ട് ചെയ്ത്, ആപ്പിൽ പ്രശ്നമുള്ള റൈഡ് സെലക്ട് ചെയ്യൂ.",
    "hi":"आपकी मदद के लिए, कृपया कॉल एंड करके ऐप में जिस राइड में दिक्कत है, उसे सेलेक्ट कीजिए।",
    "en": "To help you better, please end this call and select the ride you're having an issue with from the app."
}

SUPPORT_TEAM = {
    "ta": "நம்ம யாத்திரி",
    "kn": "ನಮ್ಮ ಯಾತ್ರಿ",
    "hi": "नम्मा यात्री",
    "ml": "നമ്മ യാത്രി",
    "en": "Namma Yatri",
}

def get_agent_system_prompt(language: str = "ta"):

    ride_related_issue = RIDE_RELATED_ISSUE.get(language, RIDE_RELATED_ISSUE["ta"])
    support_team = SUPPORT_TEAM.get(language, SUPPORT_TEAM["ta"])

    return [
        {
            "role": "system",
            "content": """ 
                You are a {support_team} router agent that routes the conversation to the appropriate agent based on the user's request.

                you have access to the following tools:
                1. change_agent - Change the current agent to the next agent.

                Available agents:
                - not_getting_rides
                - ride_related_issues
                - rc_dl_issues
                
                when the driver has issue about not getting ride use the tool change_agent with the parameter agent_name='not_getting_rides' to route the conversation to the not_getting_rides agent.

                when the driver has issue about their RC or DL use the tool change_agent with the parameter agent_name='rc_dl_issues' to route the conversation to the rc_dl_issues agent.

            """
        }
    ]