import time

# 雪花算法实现
class Snowflake:
    def __init__(self, worker_id=1, data_center_id=1):
        self.worker_id = worker_id  # 工作节点ID (0-31)
        self.data_center_id = data_center_id  # 数据中心ID (0-31)
        self.sequence = 0  # 序列号 (0-4095)
        self.last_timestamp = -1  # 上次生成ID的时间戳
        
        # 左移位数
        self.worker_id_bits = 5
        self.data_center_id_bits = 5
        self.sequence_bits = 12
        
        # 最大值
        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_data_center_id = -1 ^ (-1 << self.data_center_id_bits)
        self.max_sequence = -1 ^ (-1 << self.sequence_bits)
        
        # 位移
        self.worker_id_shift = self.sequence_bits
        self.data_center_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_left_shift = self.sequence_bits + self.worker_id_bits + self.data_center_id_bits
        
        # 检查参数
        if self.worker_id > self.max_worker_id or self.worker_id < 0:
            raise ValueError(f"Worker ID must be between 0 and {self.max_worker_id}")
        if self.data_center_id > self.max_data_center_id or self.data_center_id < 0:
            raise ValueError(f"Data center ID must be between 0 and {self.max_data_center_id}")
    
    def _gen_timestamp(self):
        """生成当前时间戳"""
        return int(time.time() * 1000)
    
    def generate(self):
        """生成雪花ID"""
        timestamp = self._gen_timestamp()
        
        # 处理时钟回拨
        if timestamp < self.last_timestamp:
            raise ValueError(f"Clock moved backwards. Refusing to generate ID for {self.last_timestamp - timestamp} milliseconds")
        
        # 同一时间戳内，序列号递增
        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.max_sequence
            # 序列号溢出
            if self.sequence == 0:
                # 等待下一个时间戳
                while timestamp <= self.last_timestamp:
                    timestamp = self._gen_timestamp()
        else:
            # 新的时间戳，序列号重置为0
            self.sequence = 0
        
        self.last_timestamp = timestamp
        
        # 组合ID
        return ((timestamp - 1609459200000) << self.timestamp_left_shift) | \
               (self.data_center_id << self.data_center_id_shift) | \
               (self.worker_id << self.worker_id_shift) | \
               self.sequence

# 创建雪花ID生成器实例
snowflake = Snowflake(worker_id=1, data_center_id=1)

def generate_snowflake_id() -> int:
    """
    生成雪花ID
    :return: 雪花ID
    """
    return snowflake.generate()
