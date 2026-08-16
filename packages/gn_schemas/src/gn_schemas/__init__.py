"""Wire contracts for Guardia Notturna.

Every service publishes and consumes these shapes. If a scanner needs a field
that is not here, add it here first - services do not extend the envelope
locally.
"""

from .alerts import Alert, AlertStatus
from .common import Actor, Entity, EntityKind, Source
from .findings import Finding, ScanResult, ScanStatus
from .intel import IpIntel, ProviderResult

__all__ = [
    "Alert",
    "AlertStatus",
    "Actor",
    "Entity",
    "EntityKind",
    "Source",
    "Finding",
    "ScanResult",
    "ScanStatus",
    "IpIntel",
    "ProviderResult",
]

__version__ = "0.1.0"
