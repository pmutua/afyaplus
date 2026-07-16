"""Regex patterns for Kenyan PII detection, shared by masking.py and demasking.py."""

import re

# +254 or a leading 0, then a Safaricom/Airtel/Telkom range (7XX or 1XX) and
# 8 more digits. Lookaround guards avoid matching inside a longer digit run
# (e.g. a member/patient ID) instead of a standalone phone number.
KENYAN_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+254|0)[17]\d{8}(?!\d)")

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# AfyaPlus member/patient ID, e.g. AP-123456. Word boundaries keep this from
# matching a 6-digit slice out of a longer ID or a mid-word "AP-".
MEMBER_ID_PATTERN = re.compile(r"\bAP-\d{6}\b")
