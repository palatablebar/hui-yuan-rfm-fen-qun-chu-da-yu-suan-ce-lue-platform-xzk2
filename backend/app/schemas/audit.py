from pydantic import BaseModel


class AuditRow(BaseModel):
    id: int
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: int | None
    created_at: str
