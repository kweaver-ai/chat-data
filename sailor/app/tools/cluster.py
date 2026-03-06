from app.tools.similarity import levenshtein_similarity


def greedy_similarity_clustering(str_list: list, min_similarity: float) -> list:
    """
    贪心聚合聚类：保证簇内两两元素相似度大于最小阈值
    :param str_list: 输入字符串列表（非空）
    :param min_similarity: 最小相似度阈值（0~1）
    :return: 聚类结果（列表的列表）
    """
    # 参数校验
    if not isinstance(str_list, list) or len(str_list) == 0:
        return []
    if not (0.0 <= min_similarity <= 1.0):
        raise ValueError("最小相似度阈值必须在0~1之间")

    # 初始化聚类结果：第一个元素作为第一个簇
    clusters = [[str_list[0]]]

    # 遍历剩余所有元素
    for current_str in str_list[1:]:
        cluster_matched = False

        # 遍历已存在的簇，尝试加入
        for cluster in clusters:
            # 检查当前元素与簇内所有元素的相似度是否都大于阈值
            all_similar_enough = True
            for elem in cluster:
                sim = levenshtein_similarity(current_str["name"], elem["name"])
                if sim <= min_similarity:
                    all_similar_enough = False
                    break  # 有一个不满足，直接跳过该簇

            # 所有元素都满足，加入该簇
            if all_similar_enough:
                cluster.append(current_str)
                cluster_matched = True
                break

        # 没有匹配到任何簇，创建新簇
        if not cluster_matched:
            clusters.append([current_str])

    return clusters

if __name__ == '__main__':
    test_strings = [
        ("apple", "x1"), ("appel", "x2"), ("aple", "x3"),  # 相似度高的一组
        ("banana", "x4"), ("banan", "x5"), ("banna", "x6"),  # 相似度高的一组
        ("orange", "x7"), ("orang", "x8"),  # 相似度高的一组
        ("grape", "x9")  # 单独一组
    ]

    # 设定最小相似度阈值（0.8）
    min_sim = 0.5

    # 执行聚类
    result = greedy_similarity_clustering(test_strings, min_sim)
    print(result)