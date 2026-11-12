"""共享枚举：角色与权限。前端 src/constants/roles.ts 同值镜像。"""

ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"
ROLES = [ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER]

ROLE_META = {
    ROLE_ADMIN: {"label": "运营主管", "hint": "分群参数、策略与预算、发布"},
    ROLE_ANALYST: {"label": "会员分析师", "hint": "跑分群、看画像、调参、导出名单"},
    ROLE_VIEWER: {"label": "店长", "hint": "只读分群结论与名单"},
}

SEGMENT_WRITE_ROLES = {ROLE_ADMIN, ROLE_ANALYST}
STRATEGY_WRITE_ROLES = {ROLE_ADMIN}
EXPORT_ROLES = {ROLE_ADMIN, ROLE_ANALYST}
ADMIN_ONLY = {ROLE_ADMIN}
