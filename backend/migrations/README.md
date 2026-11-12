# Migrations

当前演示栈在启动时用 SQLAlchemy `Base.metadata.create_all()` 建表（见
`app/config/database.py`），保证 docker compose 一键起来即可用。

`20261112_0001_initial.sql` 是等价的 PostgreSQL 16 初始 DDL，供正式环境
用 Alembic/Flyway 管理迁移时参考；演示环境不自动执行该文件。
