"""
@File: util.py
@Date:2024-02-26
@Author : Danny.gao
@Desc: 工具类
"""
from typing import List, Tuple, Any

import numpy as np
from collections import defaultdict
from app.cores.recommend.utils.algorithms import hungarian_match


def normalize_similarity_matrix(similarity_matrix, diagonal: bool = False):
    """
    归一化相似度矩阵，使得每一行和每一列的和都为 1
    :param similarity_matrix: 相似度矩阵，list[list[float]]
    :return: 归一化后的相似度矩阵，list[list[float]]
    """
    matrix = np.array(similarity_matrix, dtype=float)

    # 对角线是否设置成0：一个很小的数
    if diagonal:
        if matrix.ndim == 2:
            np.fill_diagonal(matrix, 0.01)
        else:
            diag_indices = np.diag_indices(matrix.shape[0])
            matrix[diag_indices] = 0.01

    # 行归一化
    row_sums = matrix.sum(axis=1)  # 计算每行的和
    # 使用广播机制保证矩阵除法的正确性
    normalized_matrix = matrix / row_sums[:, np.newaxis]
    return normalized_matrix


def build_similarity_matrix(
        ids_x: list[str],
        ids_y: list[str],
        search_datas: list[dict],
        normalize: bool = False,
        diagonal: bool = False,
        intersect_ids_map: dict = None
) -> list[list[float]]:
    """

    :param ids_x:
    :param ids_y:
    :param search_results:
    :return:
    """
    # 创建一个空的相似度矩阵，行数对应ids_x的个数，列数对应ids_y的个数
    num_docs_x, num_docs_y = len(ids_x), len(ids_y)
    similarity_matrix = [[0.001] * num_docs_y for _ in range(num_docs_x)]

    # 构建索引映射，以便快速查找文档的位置
    idx2index = {_: index for index, _ in enumerate(ids_x)}
    idy2index = {_: index for index, _ in enumerate(ids_y)}

    # 映射所有文档之间的得分
    visited = {}
    for idx, res in zip(ids_x, search_datas):
        for sim_doc in res:
            idy = sim_doc.get('id', '')
            if (idy and not intersect_ids_map) or (idy and intersect_ids_map and idy in intersect_ids_map.get(idx, [])):
                visited.setdefault(idx, []).append(idy)

    # 填充相似度矩阵
    for idx, res in zip(ids_x, search_datas):
        for sim_doc in res:
            idy = sim_doc.get('id', '')
            score = sim_doc.get('score', 0.0)
            if idy in visited.get(idx, []):
                source_index = idx2index[idx]
                target_index = idy2index[idy]
                similarity_matrix[source_index][target_index] = score

    if normalize:
        similarity_matrix = normalize_similarity_matrix(similarity_matrix, diagonal)

    return similarity_matrix


####################### 一致性

def aggregate_docs(ids: list[str], similarity_matrix: list[list[float]], threshold: float = 0.5) -> list[list[str]]:
    """
    根据文档间的相似度矩阵聚类文档ID。

    该函数通过设置相似度阈值来决定哪些文档ID应该聚类在一起。每个文档ID将被分配到一个聚类中，
    如果它与该聚类中的某个文档的相似度等于或大于阈值。每个聚类至少包含一个文档ID。

    参数:
    ids: 一个字符串列表，代表文档的唯一标识符。
    similarity_matrix: 一个二维浮点数列表，表示文档两两之间的相似度。
    threshold: 一个浮点数，表示文档要被归为同一聚类所需的最小相似度。默认值为0.5。

    返回:
    一个二维字符串列表，每个内部列表代表一个聚类，包含属于该聚类的文档ID。
    """
    # 初始化聚类列表和已访问索引的集合
    clusters = []
    visited = set()

    # 遍历相似度矩阵的每一行
    for i in range(len(similarity_matrix)):
        # 如果当前索引已被访问，则跳过
        if i in visited:
            continue
        # 初始化当前聚类，包含当前文档ID
        cluster = [ids[i]]
        visited.add(i)

        # 遍历当前文档与其他文档的相似度
        for j in range(len(similarity_matrix[i])):
            # 如果当前文档与另一文档的相似度等于或大于阈值，并且该文档未被访问过
            if j != i and similarity_matrix[i][j] >= threshold and j not in visited:
                # 将该文档ID添加到当前聚类，并标记为已访问
                cluster.append(ids[j])
                visited.add(j)

        # 将当前聚类添加到聚类列表
        clusters.append(cluster)

    # 返回所有聚类
    return clusters


def calculate_consistency_rate(clusters: list[list[str]], basic_info_dict: dict[str, dict],
                               group_names: list[str] = None, distinct: bool = False, i_type: str = "check_code"):
    """
    apply_type: 计算复用的方式，distinct=False表示不一致的个数（标准一致性），distinct=True表示在不同力流程中被复用的个数（指标一致性）
    """
    final_res = []
    total_data_count, consistent_data_count = 0., 0.
    for cluster in clusters:
        if group_names:

            total_data_count += len(cluster)
            join_str = '#@#@#'
            # 根据 group_names 聚合
            groups = defaultdict(list)
            for doc_id in cluster:
                if doc_id not in basic_info_dict:
                    continue

                info = basic_info_dict[doc_id]
                group_names_vs = [str(info.get(group_name, None)) for group_name in group_names]
                group_names_vs = join_str.join(group_names_vs)
                if 'name' in info:
                    item = {
                        'id': doc_id,
                        'name': info['name']
                    }
                    groups[group_names_vs].append(item)

            # 找到元素最大的组
            max_group_size = 0
            correct_name = None
            for g_name, group in groups.items():
                if len(group) > max_group_size:
                    max_group_size = len(group)
                    correct_name = g_name

            # 标记数据
            res = []
            # 一致的数据
            consistent_data = {
                'correct': True,
                'group': groups[correct_name]
            }
            for k, v in zip(group_names, correct_name.split(join_str)):
                consistent_data[k] = v
            
            res.append(consistent_data)
            # 不一致的数据
            for g_name, group in groups.items():
                if g_name != correct_name:
                    inconsistent_data = {
                        'correct': False,
                        # group_names: g_name,
                        'group': group
                    }
                    for k, v in zip(group_names, g_name.split(join_str)):
                        inconsistent_data[k] = v
                    res.append(inconsistent_data)
            consistent_data_count += len(groups[correct_name])
        else:
            # 简单聚合
            groups = []
            for doc_id in cluster:
                info = basic_info_dict.get(doc_id, {})
                name = info.get('name', '')
                if name:
                    groups.append({
                        'id': doc_id,
                        'name': name
                    })
            res = groups

        final_res.append(res)

    # 计算一致率
    if group_names:
        # inconsistent_num = total_data_count - consistent_data_count
        if i_type in ["check_code", "check_indicator"]:
            n_consistent_data_count = 0.0
            n_total_data_count = 0.0
            n_in_count = 0.0
            for i, cluster in enumerate(clusters):
                if len(cluster) > 1:
                    n_total_data_count +=  len(cluster)
                    consistent_data = final_res[i][0]
                    n_in_count += len(consistent_data["group"])

                    n_consistent_data_count += len(consistent_data["group"])

            consistency_rate = n_consistent_data_count / n_total_data_count if n_total_data_count > 0 else 0.0
            t_count = n_total_data_count
            in_count = n_in_count
        else:
            consistency_rate = consistent_data_count / total_data_count if total_data_count > 0 else 1.0
            t_count = total_data_count if distinct else len(clusters)
            in_count = 0
            for items in final_res:
                if len(items) > 1:
                    in_count += 1
    else:
        distinct_data_count = sum(len(cluster) for cluster in final_res)
        consistency_rate = distinct_data_count / total_data_count if total_data_count > 0 else 1.0
        t_count, in_count = total_data_count, total_data_count-distinct_data_count

    # # 重新计算一致性，单个点不算在聚合结果中
    # n_total_count = 0.0
    # n_consistent_data_count = 0.0
    # for cluster in final_res:
    #     n_total_count += len(cluster)
    #     if len(cluster) > 1:
    #         n_consistent_data_count += len(cluster)
    #
    # consistency_rate = n_consistent_data_count / n_total_count if n_total_count >0 else 1.0
    return final_res, consistency_rate, t_count, in_count


####################### 对齐

def match_docs(ids_x: list[str], ids_y:list[str], similarity_matrix: list[list[float]], threshold: float = 0.5) -> \
        list[tuple[Any, str | list[str], Any, str | list[str]]]:
    # step1：小于特定阈值的位置，权重设置为0
    similarity_matrix = np.array(similarity_matrix)
    similarity_matrix[similarity_matrix < threshold] = 0

    # step2：匈牙利算法找到最大权重路径
    matches = hungarian_match(similarity_matrix=similarity_matrix)

    # 构建映射列表
    mapping = [{'source': ids_x[index_x], 'target': ids_y[index_y]} for index_x, index_y in matches]

    return mapping





