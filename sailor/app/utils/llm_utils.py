# -*- coding: utf-8 -*-
# @Time    : 2026/1/4 17:52
# @Author  : Glen.lv
# @File    : llm_utils
# @Project : af-agent

import re

def estimate_tokens_safe(text: str) -> int:
    """
    Estimate the number of tokens in a given text, taking into account that Chinese characters
    are generally considered to take more space than non-Chinese characters. The function
    calculates the total token count by adding the actual length of non-Chinese characters and
    multiplying the number of Chinese characters found in the text by 1.4.

    :returns: int - The estimated number of tokens in the provided text.
    :raises: This function does not explicitly raise any exceptions, but it may raise
             exceptions from the re module if the input is not a string or if there are
             issues with the regular expression used for finding Chinese characters.
    :param text: str - The text for which the token count needs to be estimated. It can
                       contain a mix of Chinese and non-Chinese (e.g., English, digits,
                       punctuation) characters.
    """
    chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 所有非中文字符（包括英文、数字、符号）按字符数算
    non_chinese = len(text) - chinese
    return int(non_chinese + chinese * 1.4)
