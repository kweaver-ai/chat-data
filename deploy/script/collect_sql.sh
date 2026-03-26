#!/bin/bash

# 收集 SQL 文件的脚本
# 使用方法：在 Bash 中运行 bash collect_sql.sh

# 脚本所在目录的父目录（即 adp 目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DR_DIR="$(dirname "$SCRIPT_DIR")"
echo "工作目录: $DR_DIR"

# 来源目录列表
SRC_DIRS=(
    "../sailor-agent/migrations"
    "../sailor-service/migrations"
)

# 数据库类型列表
DB_TYPES=("dm8" "mariadb")

# 目标目录（与 script 同级）
DST_DIR="$DR_DIR/sql"
if [ ! -d "$DST_DIR" ]; then
    mkdir -p "$DST_DIR"
fi

# 为每个数据库类型创建临时文件
TMP_FILES=()
DB_TYPE_MAP=()
index=0
for db_type in "${DB_TYPES[@]}"; do
    TMP_FILES[$index]=$(mktemp)
    DB_TYPE_MAP[$index]=$db_type
    index=$((index + 1))
done

# 清理函数
cleanup() {
    for tmp_file in "${TMP_FILES[@]}"; do
        if [ -f "$tmp_file" ]; then
            rm -f "$tmp_file"
        fi
    done
}

# 设置退出时清理
trap cleanup EXIT

# 遍历每个来源目录
for dir in "${SRC_DIRS[@]}"; do
    FULL_DIR="$DR_DIR/$dir"
    echo "处理目录: $FULL_DIR"
    
    # 遍历每个数据库类型
    for db_type in "${DB_TYPES[@]}"; do
        DB_DIR="$FULL_DIR/$db_type"
        echo "  数据库目录: $DB_DIR"
        echo "  目录是否存在: $([ -d "$DB_DIR" ] && echo "True" || echo "False")"
        
        if [ ! -d "$DB_DIR" ]; then
            echo "  警告: 目录不存在 $DB_DIR"
            continue
        fi
        
        # 找到版本号最大的文件夹
        VERSION_DIRS=$(find "$DB_DIR" -maxdepth 1 -type d -name "*.*.*" | sort -V | tail -1)
        
        if [ -z "$VERSION_DIRS" ]; then
            echo "  警告: 在 $DB_DIR 中未找到版本目录"
            continue
        fi
        
        # 获取最新版本目录名
        LATEST=$(basename "$VERSION_DIRS")
        echo "  找到最新版本: $LATEST"
        
        # 检查 init.sql 是否在 pre/ 子目录中
        INIT_SQL="$VERSION_DIRS/pre/init.sql"
        
        if [ ! -f "$INIT_SQL" ]; then
            echo "  错误: 在 $VERSION_DIRS/pre/init.sql 中未找到 init.sql 文件"
            exit 1
        fi
        
        echo "  合并文件: $INIT_SQL"
        
        # 将绝对路径转换为相对路径
        RELATIVE_PATH="${INIT_SQL#$DR_DIR/}"
        
        # 写入对应的临时文件
        # 找到当前数据库类型对应的索引
        for i in "${!DB_TYPE_MAP[@]}"; do
            if [ "${DB_TYPE_MAP[$i]}" = "$db_type" ]; then
                tmp_file="${TMP_FILES[$i]}"
                break
            fi
        done
        # 如果文件不为空，先添加一个换行符
        if [ -s "$tmp_file" ]; then
            echo "" >> "$tmp_file"
        fi
        echo "-- Source: $RELATIVE_PATH" >> "$tmp_file"
        cat "$INIT_SQL" | tr -d '\r' >> "$tmp_file"
    done
done

# 合并结果写入目标文件
for i in "${!DB_TYPE_MAP[@]}"; do
    db_type="${DB_TYPE_MAP[$i]}"
    tmp_file="${TMP_FILES[$i]}"
    DEST_FILE="$DST_DIR/${db_type}_init.sql"
    mv "$tmp_file" "$DEST_FILE"
    echo "已生成 $DEST_FILE"
done
