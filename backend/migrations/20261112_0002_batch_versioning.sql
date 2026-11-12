-- 分群批次版本化 + 整批校验报告（在 20261112_0001_initial.sql 之后执行）
-- 设计要点：
-- 1. 历史批次全部保留，仅 is_current=TRUE 的批次为「当前版本」，同一时刻至多一条；
-- 2. input_fingerprint 覆盖会员/订单事实内容，同一补录重复运行命中同一指纹 → 直接复用旧批次；
-- 3. validation_report 存整批校验结果（会员/订单/簇人数对账），失败批次保留报告但不切换当前版本。
ALTER TABLE segment_runs
    ADD COLUMN IF NOT EXISTS is_current        BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS current_since     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS input_fingerprint VARCHAR(64),
    ADD COLUMN IF NOT EXISTS validation_report JSONB;

-- 同一输入指纹（含 as-of / k / 数据内容）只允许一个有效批次，重复补录走幂等复用。
CREATE UNIQUE INDEX IF NOT EXISTS uq_runs_fingerprint
    ON segment_runs (input_fingerprint)
    WHERE input_fingerprint IS NOT NULL AND status <> 'failed';

CREATE INDEX IF NOT EXISTS idx_runs_current ON segment_runs (is_current) WHERE is_current;
CREATE INDEX IF NOT EXISTS idx_runs_as_of ON segment_runs (as_of);
