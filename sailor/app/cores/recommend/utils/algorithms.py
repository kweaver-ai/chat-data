"""
@File: algorithms.py
@Date: 2024-12-23
@Author: Danny.gao
@Desc: 
"""

import numpy as np
from scipy.optimize import linear_sum_assignment


# 匈牙利匹配算法
def hungarian_match(similarity_matrix):
    # 将相似度矩阵转换为代价矩阵（取负值）
    cost_matrix = -np.array(similarity_matrix)

    # 应用匈牙利算法
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # 构建匹配结果
    matches = [(i, j) for i, j in zip(row_ind, col_ind)]

    return matches
