from enum import Enum

from app.logs.logger import logger


class ModelType4Prompt(Enum):
    """
    Model type for prompt
    We need to customize the prompt for different models in some cases.
    """
    GPT4O = "gpt-4o"
    LANGCHAIN = "langchain"
    DEEPSEEK_R1 = "deepseek-r1"
    # DeepSeek V3.2 系列（含 -vol 等部署后缀）：强约束、精简 prompt
    DEEPSEEK_V32 = "deepseek-v3.2"
    DEFAULT = "default"

    @classmethod
    def values(cls):
        return [mt.value for mt in cls]

    @classmethod
    def keys(cls):
        return [mt.name for mt in cls]


def get_standard_model_type(model_type: str):
    """ Get standard model type
    """
    if isinstance(model_type, ModelType4Prompt):
        return model_type.value

    if not model_type:
        model_type = ModelType4Prompt.DEFAULT.value
    else:
        model_type = model_type.lower()

    # 将 DeepSeek V3.2 系列部署名统一为 canonical，便于选择专用 prompt
    if model_type.startswith("deepseek-v3.2") or model_type.startswith("deepseek-v3-2"):
        model_type = ModelType4Prompt.DEEPSEEK_V32.value

    if model_type not in ModelType4Prompt.values():
        logger.warning(f"model_type: {model_type} not found, use default model_type: {ModelType4Prompt.DEFAULT.value}")
        logger.info(f"supported model_type: {ModelType4Prompt.values()}")
        model_type = ModelType4Prompt.DEFAULT.value
    else:
        logger.info(f"model_type: {model_type}")

    return model_type
