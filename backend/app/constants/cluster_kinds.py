"""共享枚举：分群簇类型（后端权威定义）。

前端 `src/constants/clusterKinds.ts` 保留同值镜像，仅用于展示文案；
簇类型的判定始终由后端 rfm_engine.label_cluster() 计算，前端不参与。
"""

CLUSTER_KIND_META = {
    "HIGH_VALUE_DORMANT": {
        "label": "高价值沉睡",
        "short": "沉睡",
        "advice": "历史客单与频次高但近半年未到店，优先用中等面额唤醒券 + 店长企微一对一。",
    },
    "CORE_ACTIVE": {
        "label": "核心活跃",
        "short": "核心",
        "advice": "近期高频高客单，维持权益感（升杯/限定豆）而非大额折扣。",
    },
    "NEW_NURTURE": {
        "label": "新客培育",
        "short": "新客",
        "advice": "到店近但频次低，用小面额第二杯券拉第二次消费。",
    },
    "PRICE_SENSITIVE": {
        "label": "价格敏感",
        "short": "敏感",
        "advice": "核销率高、客单低，适合固定面额券做高频复购，控制单券成本。",
    },
    "LOW_FREQ_CHURN": {
        "label": "低频流失",
        "short": "流失",
        "advice": "久未到店且频次低，先低成本触达测试，不建议占用大额预算。",
    },
    "STABLE_POTENTIAL": {
        "label": "稳定潜力",
        "short": "稳定",
        "advice": "画像居中的稳定客群，用标准复购券滚动维护。",
    },
}

CLUSTER_KIND_ORDER = [
    "HIGH_VALUE_DORMANT",
    "CORE_ACTIVE",
    "NEW_NURTURE",
    "PRICE_SENSITIVE",
    "LOW_FREQ_CHURN",
    "STABLE_POTENTIAL",
]
