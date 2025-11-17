blocked_reason_messages = {
    "BLOCKED_BASED_ON_CANCELLATION_RATE" : "Your account has been blocked due to frequent cancellations of rides. Our system has detected multiple cancellations, which violate our policy.",
    "BLOCKED_BASED_ON_UNPAID_DUES": "Your account has been blocked because there are unpaid dues associated with your account.",
    "BLOCKED_BASED_ON_OVERCHARGED": "Your account has been blocked due to the collection of unauthorized extra charges from the passenger, including toll charges or overcharging.",
    "BLOCKED_BASED_ON_MISBEHAVING" : "Your account has been blocked due to reports of misbehavior with a passenger during a ride. Yatri Sathi has a zero-tolerance policy for such behavior.",
    "BLOCKED_BASED_ON_DRUNK_AND_DRIVING": "Your account has been blocked because you were found to be driving under the influence of alcohol or drugs while on duty. This is a serious violation of our safety guidelines."
}



def get_blocked_reason_message(blocked_reason: str) -> str:
    if blocked_reason in blocked_reason_messages:
        return blocked_reason_messages[blocked_reason]
    else:
        return "Your account has been blocked due to a violation of our policy. Please contact support for more information."