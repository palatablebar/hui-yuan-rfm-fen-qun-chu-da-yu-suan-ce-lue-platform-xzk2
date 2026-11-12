from pydantic import BaseModel


class MemberRow(BaseModel):
    id: int
    member_no: str
    name: str
    phone: str
    store_code: str
    store_name: str
    joined_at: str
    consent: bool
