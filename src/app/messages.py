"""
messages.py — Fokiz message bank and tone selection.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- No DB access, no math, no I/O.
- Pure data + selection logic.
"""

import random
from .math_engine import Zone, DeltaStatus
from .i18n import _

# ---------------------------------------------------------------------------
# Message banks by zone/tone
# ---------------------------------------------------------------------------

_MESSAGES_GREEN = [
    "msg.green.1", "msg.green.2", "msg.green.3", "msg.green.4", "msg.green.5"
]

_MESSAGES_YELLOW = [
    "msg.yellow.1", "msg.yellow.2", "msg.yellow.3", "msg.yellow.4", "msg.yellow.5", "msg.yellow.6"
]

_MESSAGES_ORANGE = [
    "msg.orange.1", "msg.orange.2", "msg.orange.3", "msg.orange.4", "msg.orange.5", "msg.orange.6"
]

_MESSAGES_RED = [
    "msg.red.1", "msg.red.2", "msg.red.3", "msg.red.4", "msg.red.5"
]

_MESSAGES_EXPIRED = [
    "msg.expired.1", "msg.expired.2", "msg.expired.3", "msg.expired.4", "msg.expired.5"
]

_MESSAGES_WAKEUP = [
    "msg.wakeup.1", "msg.wakeup.2", "msg.wakeup.3", "msg.wakeup.4", "msg.wakeup.5"
]

_MESSAGES_SURRENDER = [
    "msg.surrender.1", "msg.surrender.2", "msg.surrender.3"
]

_MESSAGES_MADRUGADA = [
    "msg.madrugada.1", "msg.madrugada.2", "msg.madrugada.3"
]

# ---------------------------------------------------------------------------
# Summary tone by delta
# ---------------------------------------------------------------------------

def get_delta_label(status: DeltaStatus) -> str:
    mapping = {
        DeltaStatus.AHEAD: "delta.ahead",
        DeltaStatus.ON_TRACK: "delta.on_track",
        DeltaStatus.BEHIND: "delta.behind",
    }
    return _(mapping[status])


# ---------------------------------------------------------------------------
# Message selection
# ---------------------------------------------------------------------------

def pick_message(zone: Zone, wakeup: bool = False, nickname: str = "User", local_hour: int = 12) -> str:
    is_madrugada = (0 <= local_hour < 5)
    
    if wakeup:
        bank_group = _MESSAGES_WAKEUP
    elif is_madrugada and zone in (Zone.YELLOW, Zone.ORANGE, Zone.RED) and random.random() < 0.5:
        bank_group = _MESSAGES_MADRUGADA
    else:
        banks = {
            Zone.GREEN: _MESSAGES_GREEN,
            Zone.YELLOW: _MESSAGES_YELLOW,
            Zone.ORANGE: _MESSAGES_ORANGE,
            Zone.RED: _MESSAGES_RED,
            Zone.EXPIRED: _MESSAGES_EXPIRED,
        }
        bank_group = banks[zone]
        
    msg_key = random.choice(bank_group)
    msg = _(msg_key)
    
    if bank_group != _MESSAGES_MADRUGADA and "{nickname}" not in msg:
        if random.random() < 0.3:
            msg = f"{nickname}, {msg[0].lower()}{msg[1:]}" if msg[0].isalpha() else f"{msg} ({nickname})"
            
    return msg.format(nickname=nickname)


def pick_surrender_message() -> str:
    msg_key = random.choice(_MESSAGES_SURRENDER)
    return _(msg_key)


def urgency_label(zone: Zone) -> str:
    urgency_map = {
        Zone.GREEN: "urgency.low",
        Zone.YELLOW: "urgency.medium",
        Zone.ORANGE: "urgency.high",
        Zone.RED: "urgency.critical",
        Zone.EXPIRED: "urgency.critical",
    }
    return _(urgency_map[zone])
