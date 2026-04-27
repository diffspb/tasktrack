import uuid
from dataclasses import dataclass, field


@dataclass
class StubUser:
    id: uuid.UUID = field(
        default_factory=lambda: uuid.UUID("00000000-0000-0000-0000-000000000001")
    )
    email: str = "dev@localhost"
    display_name: str = "Dev User"
    is_active: bool = True
    keycloak_id: str = "00000000-0000-0000-0000-000000000001"


STUB_USER = StubUser()
