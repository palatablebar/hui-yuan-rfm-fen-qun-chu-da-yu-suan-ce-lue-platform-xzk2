"""会员主数据查询（RFM 明细页 / 名单页共用）。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Member
from app.utils.pagination import page_params, paginated


def serialize_member(member: Member) -> dict:
    return {
        "id": member.id,
        "member_no": member.member_no,
        "name": member.name,
        "phone": member.phone,
        "store_code": member.store_code,
        "store_name": member.store_name,
        "joined_at": member.joined_at.isoformat(),
        "consent": member.consent,
    }


def list_members(
    db: Session,
    search: str | None = None,
    store_code: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
) -> dict:
    current, size = page_params(page, page_size)
    stmt = select(Member)
    if store_code:
        stmt = stmt.where(Member.store_code == store_code)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Member.member_no.ilike(like), Member.name.ilike(like), Member.phone.ilike(like))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Member.member_no).offset((current - 1) * size).limit(size)
    ).all()
    return paginated([serialize_member(row) for row in rows], total, current, size)


def list_stores(db: Session) -> list[dict]:
    rows = db.execute(
        select(Member.store_code, Member.store_name, func.count(Member.id))
        .group_by(Member.store_code, Member.store_name)
        .order_by(Member.store_code)
    ).all()
    return [
        {"store_code": code, "store_name": name, "member_count": count}
        for code, name, count in rows
    ]


def load_member_map(db: Session, member_ids: list[int]) -> dict[int, Member]:
    if not member_ids:
        return {}
    rows = db.scalars(select(Member).where(Member.id.in_(member_ids))).all()
    return {row.id: row for row in rows}
