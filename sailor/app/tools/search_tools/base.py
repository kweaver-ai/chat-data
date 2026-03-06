from enum import Enum

class QueryIntentionName(Enum):
    INTENTION_GENERIC_DEMAND = "宽泛的需求"
    INTENTION_SPECIFIC_DEMAND = "明确指向的需求"
    INTENTION_OUT_OF_SCOPE = "不在支持范围内"
    INTENTION_UNKNOWN  = "未知意图"