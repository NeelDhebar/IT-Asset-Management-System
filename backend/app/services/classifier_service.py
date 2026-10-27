"""Rule-Based Automatic Ticket Classification Engine.

Demonstrates:
- Regular expressions (re module)
- String manipulations
- Dictionaries & Taxonomy Mappings
- Higher-Order Functions: lambda, filter
- List and Dictionary Comprehensions
- Pure Python algorithmic logic (No external LLM)
"""

import re
from typing import Dict, List, Tuple
from app.models.enums import TicketCategory, TicketPriority


class TicketClassifier:
    """Classifies ticket title and description into Category and Priority based on rule heuristics."""

    # Taxonomy mapping for Categories with regex patterns
    CATEGORY_PATTERNS: Dict[TicketCategory, List[str]] = {
        TicketCategory.HARDWARE: [
            r"\b(laptop|desktop|monitor|screen|keyboard|mouse|printer|battery|charger|hard disk|ram|motherboard|fan|power)\b",
            r"\b(broken|cracked|physical damage|not turning on|not starting|overheating|spilled|beep)\b",
        ],
        TicketCategory.SOFTWARE: [
            r"\b(windows|linux|macos|excel|word|teams|slack|zoom|outlook|ms office|office 365|browser|chrome|firefox)\b",
            r"\b(install|uninstall|update|crash|blue screen|bsod|freeze|license|activation|bug|error code)\b",
        ],
        TicketCategory.NETWORK: [
            r"\b(wifi|wi-fi|ethernet|internet|lan|wan|vpn|router|dns|ip address|firewall|proxy)\b",
            r"\b(slow internet|disconnected|no connection|connect|connection|packet loss|gateway timeout|unreachable|outage)\b",
        ],
        TicketCategory.ACCESS: [
            r"\b(password|login|credentials|permission|access|account locked|reset password|mfa|2fa|otp|sso)\b",
            r"\b(unauthorized|expired|privileges|role|vpn access|door badge)\b",
        ],
    }

    # Urgency indicators for Priority scoring
    CRITICAL_KEYWORDS: List[str] = [
        "outage", "entire floor", "production down", "critical", "urgent", "emergency",
        "data loss", "ransomware", "server down", "blocked all work", "fire"
    ]
    HIGH_KEYWORDS: List[str] = [
        "not starting", "cannot work", "deadline", "crash", "asap", "high priority",
        "broken screen", "not working", "fails completely", "locked out"
    ]
    MEDIUM_KEYWORDS: List[str] = [
        "slow", "intermittent", "glitch", "warning", "display flickering", "performance",
        "restart needed", "partial access"
    ]

    def __init__(self) -> None:
        # Pre-compile regex patterns for performance
        self._compiled_category_rules = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in self.CATEGORY_PATTERNS.items()
        }

    def classify(self, title: str, description: str) -> Tuple[TicketCategory, TicketPriority, List[str]]:
        """Classify a ticket text into Category and Priority.

        Uses string operations, regex, list comprehensions, filter, and lambda.
        """
        combined_text = f"{title.strip().lower()} {description.strip().lower()}"

        # 1. Category Matching using regex & comprehensions
        category_scores: Dict[TicketCategory, int] = {}
        matched_category_keywords: Dict[TicketCategory, List[str]] = {}

        for category, patterns in self._compiled_category_rules.items():
            matches = [
                match.group()
                for pattern in patterns
                for match in pattern.finditer(combined_text)
            ]
            category_scores[category] = len(matches)
            matched_category_keywords[category] = matches

        # Use max with key lambda to find the highest scoring category
        best_category = max(category_scores.items(), key=lambda item: item[1])

        # If no keywords matched, default to OTHER
        selected_category = (
            best_category[0] if best_category[1] > 0 else TicketCategory.OTHER
        )

        # 2. Priority Determination using filter, lambda, and string operations
        critical_matches = list(
            filter(lambda kw: kw in combined_text, self.CRITICAL_KEYWORDS)
        )
        high_matches = list(
            filter(lambda kw: kw in combined_text, self.HIGH_KEYWORDS)
        )
        medium_matches = list(
            filter(lambda kw: kw in combined_text, self.MEDIUM_KEYWORDS)
        )

        if critical_matches:
            selected_priority = TicketPriority.CRITICAL
            matched_priority_kws = critical_matches
        elif high_matches:
            selected_priority = TicketPriority.HIGH
            matched_priority_kws = high_matches
        elif medium_matches:
            selected_priority = TicketPriority.MEDIUM
            matched_priority_kws = medium_matches
        else:
            selected_priority = TicketPriority.LOW
            matched_priority_kws = ["default_low_heuristic"]

        # Aggregate all matched keywords using list comprehension
        all_matched = [
            kw for kw in (matched_category_keywords.get(selected_category, []) + matched_priority_kws)
            if kw
        ]

        return selected_category, selected_priority, all_matched


# Convenience singleton function
_classifier_instance = TicketClassifier()


def auto_classify_ticket(title: str, description: str) -> Tuple[TicketCategory, TicketPriority, List[str]]:
    """Classify ticket attributes automatically from title and description."""
    return _classifier_instance.classify(title, description)
