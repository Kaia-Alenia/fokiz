"""
messages.py — Fokiz message bank and tone selection.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- No DB access, no math, no I/O.
- Pure data + selection logic.
"""

import random
from .math_engine import Zone, DeltaStatus
from .i18n import CURRENT_LANG

# ---------------------------------------------------------------------------
# Message banks by zone/tone
# ---------------------------------------------------------------------------

_MESSAGES_GREEN = {
    "es": [
        "Vas bien. No te duermas.",
        "Todavía hay tiempo. No lo desperdicies.",
        "El plazo sigue ahí, esperándote.",
        "Buen ritmo. Mantén el paso.",
        "El contrato recuerda lo que prometiste.",
    ],
    "en": [
        "You're doing well. Don't fall asleep.",
        "There's still time. Don't waste it.",
        "The deadline is still there, waiting for you.",
        "Good pace. Keep it up.",
        "The contract remembers what you promised.",
    ]
}

_MESSAGES_YELLOW = {
    "es": [
        "El tiempo corre. ¿Estás avanzando?",
        "La mitad del camino ya pasó. ¿Dónde está tu progreso?",
        "¿Ya olvidaste lo que te comprometiste a hacer?",
        "El reloj no se detiene aunque tú sí.",
        "Zona amarilla. No es señal de ceder.",
        "Medio tiempo. Las excusas no cuentan como progreso.",
    ],
    "en": [
        "Time is ticking. Are you making progress?",
        "Half the time is gone. Where is your progress?",
        "Did you forget what you committed to?",
        "The clock doesn't stop even if you do.",
        "Yellow zone. Not a signal to yield.",
        "Halftime. Excuses don't count as progress.",
    ]
}

_MESSAGES_ORANGE = {
    "es": [
        "El tiempo se acaba. Espabila.",
        "¿Todavía en esto? El plazo no es opcional.",
        "Zona naranja. Cada minuto desperdiciado es tuyo.",
        "Urgencia real. No simulada. Muévete.",
        "El contrato no va a renegociarse solo porque no avanzaste.",
        "¿Sabías que la procrastinación también tiene plazos?",
    ],
    "en": [
        "Time is running out. Wake up.",
        "Still on this? The deadline is not optional.",
        "Orange zone. Every wasted minute is yours.",
        "Real urgency. Not simulated. Move.",
        "The contract won't renegotiate just because you didn't advance.",
        "Did you know procrastination has deadlines too?",
    ]
}

_MESSAGES_RED = {
    "es": [
        "ÚLTIMA OPORTUNIDAD. ¿Qué estás esperando?",
        "Ya casi no hay margen. Este es el momento.",
        "El deadline está ahí. Tú también. Haz algo.",
        "El contrato vence pronto. Sin excepciones.",
        "Zona roja. No hay tiempo para distracciones.",
    ],
    "en": [
        "LAST CHANCE. What are you waiting for?",
        "Almost no margin left. This is the moment.",
        "The deadline is there. You too. Do something.",
        "The contract expires soon. No exceptions.",
        "Red zone. No time for distractions.",
    ]
}

_MESSAGES_EXPIRED = {
    "es": [
        "VENCIDO. El plazo pasó. Registra tu falla o ríndete.",
        "El contrato ya expiró. El registro queda permanente.",
        "Fase vencida. Fokiz sigue. El contrato sigue.",
        "Ya era tarde antes. Ahora es peor.",
        "Sin excusas. La fecha límite no espera.",
    ],
    "en": [
        "EXPIRED. The time has passed. Register your failure or surrender.",
        "The contract has expired. The record is permanent.",
        "Expired phase. Fokiz continues. The contract continues.",
        "It was late before. Now it's worse.",
        "No excuses. The deadline waits for no one.",
    ]
}

_MESSAGES_WAKEUP = {
    "es": [
        "¡Bienvenido de vuelta! El contrato no tomó un descanso.",
        "Volviste. El plazo tampoco se fue.",
        "Fin del descanso. El trabajo sigue esperando.",
        "Reanudaste la sesión. El contrato también reanuda el cargo.",
        "¿Descansado? El deadline no lo está.",
    ],
    "en": [
        "Welcome back! The contract didn't take a break.",
        "You're back. The deadline hasn't left either.",
        "End of the break. The work is still waiting.",
        "Session resumed. The contract resumes charge as well.",
        "Rested? The deadline isn't.",
    ]
}

_MESSAGES_SURRENDER = {
    "es": [
        "Rendición registrada. La historia queda intacta.",
        "El contrato permanece. La rendición también.",
        "Fokiz registra todo. Esta decisión también.",
    ],
    "en": [
        "Surrender registered. History remains intact.",
        "The contract remains. So does the surrender.",
        "Fokiz records everything. This decision too.",
    ]
}


# ---------------------------------------------------------------------------
# Summary tone by delta
# ---------------------------------------------------------------------------

def get_delta_label(status: DeltaStatus) -> str:
    mapping = {
        DeltaStatus.AHEAD: {"es": "ADELANTADO — Zona de tregua", "en": "AHEAD — Truce zone"},
        DeltaStatus.ON_TRACK: {"es": "AL DÍA — Mantén el ritmo", "en": "ON TRACK — Keep the pace"},
        DeltaStatus.BEHIND: {"es": "ATRASADO — Hostigamiento activo", "en": "BEHIND — Active harassment"},
    }
    return mapping[status].get(CURRENT_LANG, mapping[status]["es"])


# ---------------------------------------------------------------------------
# Message selection
# ---------------------------------------------------------------------------

def pick_message(zone: Zone, wakeup: bool = False) -> str:
    if wakeup:
        bank_group = _MESSAGES_WAKEUP
    else:
        banks = {
            Zone.GREEN: _MESSAGES_GREEN,
            Zone.YELLOW: _MESSAGES_YELLOW,
            Zone.ORANGE: _MESSAGES_ORANGE,
            Zone.RED: _MESSAGES_RED,
            Zone.EXPIRED: _MESSAGES_EXPIRED,
        }
        bank_group = banks[zone]
        
    bank = bank_group.get(CURRENT_LANG, bank_group["es"])
    return random.choice(bank)


def pick_surrender_message() -> str:
    bank = _MESSAGES_SURRENDER.get(CURRENT_LANG, _MESSAGES_SURRENDER["es"])
    return random.choice(bank)


def urgency_label(zone: Zone) -> str:
    labels = {
        Zone.GREEN: {"es": "BAJA", "en": "LOW"},
        Zone.YELLOW: {"es": "MEDIA", "en": "MEDIUM"},
        Zone.ORANGE: {"es": "ALTA", "en": "HIGH"},
        Zone.RED: {"es": "CRÍTICA", "en": "CRITICAL"},
        Zone.EXPIRED: {"es": "CRÍTICA", "en": "CRITICAL"},
    }
    return labels[zone].get(CURRENT_LANG, labels[zone]["es"])
