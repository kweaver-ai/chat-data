def levenshtein_similarity(str1: str, str2: str) -> float:
    """
    计算两个字符串的编辑距离相似度（0~1之间，1表示完全相同）
    :param str1: 第一个字符串
    :param str2: 第二个字符串
    :return: 相似度得分
    """
    # 获取两个字符串的长度
    m, n = len(str1), len(str2)

    # 创建动态规划二维数组，dp[i][j]表示str1前i个字符转为str2前j个字符的最小编辑距离
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 初始化边界：一个字符串为空，转为另一个字符串需要插入全部字符
    for i in range(m + 1):
        dp[i][0] = i  # str1前i个字符转为空字符串，需要删除i次
    for j in range(n + 1):
        dp[0][j] = j  # 空字符串转为str2前j个字符，需要插入j次

    # 填充动态规划数组
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # 如果当前字符相同，无需额外操作，继承前一个状态的距离
            if str1[i - 1] == str2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                # 否则，取「删除、插入、替换」三种操作的最小距离+1
                dp[i][j] = 1 + min(
                    dp[i - 1][j],  # 删除：str1删除第i个字符，匹配str2前j个字符
                    dp[i][j - 1],  # 插入：str1插入一个字符，匹配str2第j个字符
                    dp[i - 1][j - 1]  # 替换：str1第i个字符替换为str2第j个字符
                )

    # 转换为相似度：(最大可能距离 - 实际编辑距离) / 最大可能距离
    max_distance = max(m, n)
    if max_distance == 0:
        return 1.0  # 两个空字符串相似度为1
    return 1.0 - (dp[m][n] / max_distance)

if __name__ == '__main__':
    print(levenshtein_similarity("计划计划", "计划"))