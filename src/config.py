# config.py
import logging
import os
import re

# --- Basic Configuration ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Speaker IDs ---
AGENT_SPEAKER_ID = "agent"
BORROWER_SPEAKER_ID = "customer"

# --- LLM Configuration ---
GEMINI_MODEL_NAME = "gemini-2.0-flash-lite"  # Example model
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# --- Regex Patterns & Lists ---

# Profanity
PROFANE_WORDS = [
    "fuck",
    "fucking",
    "fucker",
    "fuckhead",
    "fuckwit",
    "motherfucker",
    "shit",
    "shitty",
    "shitting",
    "shithead",
    "bullshit",
    "dipshit",
    "ass",
    "asshole",
    "asshat",
    "jackass",
    "dumbass",
    "bitch",
    "bitching",
    "son of a bitch",
    "bastard",
    "cunt",
    "damn",
    "damnit",
    "goddamn",
    "god dammit",
    "god damn",
    "hell",
    "what the hell",
    "crap",
    "crappy",
    "piss",
    "pissed",
    "piss off",
    "dick",
    "dickhead",
    "cock",
    "cocksucker",
    "slut",
    "whore",
    "bloody",
    "bugger",
    "screw you",
    "screwed",
    "jerk",
    "idiot",
    "moron",
    "stupid",
]
PROFANITY_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in PROFANE_WORDS) + r")\b",
    re.IGNORECASE,
)

# Privacy - Sensitive Info
SENSITIVE_INFO_KEYWORDS = [
    "account number",
    "account no",
    "acct number",
    "account #",
    "balance",
    "outstanding balance",
    "amount due",
    "owe",
    "how much do i owe",
    "payment",
    "payment amount",
    "payment date",
    "due date",
    "past due",
    "credit card number",
    "card number",
    "cc number",
    "visa",
    "mastercard",
    "amex",
    "social security number",
    "ssn",
    "social",
    "bank account",
    "routing number",
    "loan number",
    "loan id",
    "personal identification number",
    "pin",
]
SENSITIVE_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in SENSITIVE_INFO_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Privacy - Verification
VERIFICATION_KEYWORDS = [
    "date of birth",
    "dob",
    "birth date",
    "verify your address",
    "confirm your address",
    "address on file",
    "mailing address",
    "physical address",
    "social security number",
    "ssn",
    "last four digits of your social",
    "last 4 of social",
    "verify your identity",
    "confirm your identity",
    "verify information",
    "mother's maiden name",
    "maiden name",
    "security question",
    "security word",
    "account number",
    "zip code",
    "postal code",
    "phone number on file",
    "confirm this phone number",
    "last four digits",
    "last 4 digits",
    "verify",
    "confirm",
    "authenticate",
]
VERIFY_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in VERIFICATION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# --- Add other constants as needed ---
