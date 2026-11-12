# Migrations

当前演示栈在启动时用 SQLAlchemy `Base.metadata.create_all()` 建表（见
`app/config/database.py`），保证 docker compose 一键起来即可用。

`20261112_0001_initial.sql` 是等价的 PostgreSQL 16 初始 DDL，供正式环境
用 Alembic/Flyway 管理迁移时参考；演示环境不自动执行该文件。

`20261112_0002_batch_versioning.sql` 在初始表之上增加分群批次版本化能力
（`is_current / current_since / input_fingerprint / validation_report`
及指纹唯一索引、当前版本部分索引）。演示环境同样由 `create_all()` 按
SQLAlchemy 模型自动建出这些列；正式环境按序号顺序执行两个 SQL 文件。
