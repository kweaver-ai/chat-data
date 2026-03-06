from enum import Enum, unique


@unique
class T2SConfig(Enum):
    TIMES: int = 3
    timeout: int = 300000


class MySQLKeyword:
    MAP_TYPE = {
        "0": "int",
        "1": "varchar(255)",
        "2": "data",
        "3": "datetime",
        "4": "timestamp",
        "5": "bool",
        "6": "binary",
        "7": "varchar(50)"
    }
    SELECT = "SELECT"

    IN = [
        "in", "IN"
    ]
    AS = [
        "AS", "as"
    ]
    AND = [
        "AND", "and"
    ]
    BY = [
        "BY", "by"
    ]
    ORDER = [
        "ORDER", "order"
    ]
    BETWEEN = [
        "BETWEEN", "between"
    ]
    DATE = [
        "2", "3", "4",
        "timestamp", "datetime", "date", "time", "year", "timestamp with time zone", "time with time zone'",
        "DATE", "TIME", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIME WITH TIME ZONE",
    ]  # 代表时间型 DATE '2022-11-22'
    STR = [
        "1", "varchar", "char", "CHAR", "VARCHAR",
    ]  # 代表字符型，可以加引号
    SYMBOLS = [
        "=", ">", "<", ">=", "<=", "!=", "<>", "LIKE", "BETWEEN",
    ]
    QUOTE = [
        "，", "。", ",", "."
    ]
    DIGIT = [
        "零", "一", "二", "三", "四", "五", "六", "七", "八", "九",
        "零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖",
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "(", "%",
    ]
