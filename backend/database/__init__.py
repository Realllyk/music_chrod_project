"""
数据库连接模块
负责 MySQL 数据库连接管理
"""

import pymysql
from pathlib import Path
import json


class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self):
        """从配置文件加载数据库配置"""
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('database', {})
    
    @property
    def enabled(self):
        return self._config.get('enabled', False)
    
    @property
    def host(self):
        return self._config.get('host', 'localhost')
    
    @property
    def port(self):
        return int(self._config.get('port', 3306))
    
    @property
    def database(self):
        return self._config.get('database', 'music_db')
    
    @property
    def user(self):
        return self._config.get('user', 'root')
    
    @property
    def password(self):
        return self._config.get('password', '')
    
    @property
    def charset(self):
        return self._config.get('charset', 'utf8mb4')
    
    def to_dict(self):
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'charset': self.charset
        }


class DatabaseConnection:
    """数据库连接管理类"""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = DatabaseConfig()
        return cls._instance
    
    def get_connection(self):
        """获取数据库连接"""
        if not self._config.enabled:
            return None
        
        # 检查现有连接是否有效
        if self._connection:
            try:
                self._connection.ping(reconnect=True)
                return self._connection
            except:
                self._connection = None
        
        try:
            self._connection = pymysql.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                database=self._config.database,
                charset=self._config.charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            return self._connection
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None
    
    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    @property
    def config(self):
        return self._config


def get_db():
    """获取数据库连接（便捷函数）"""
    return DatabaseConnection().get_connection()


def test_connection(config_dict=None):
    """
    测试数据库连接
    
    Args:
        config_dict: 可选的配置字典
    
    Returns:
        tuple: (成功标志, 错误信息)
    """
    if config_dict is None:
        config_dict = DatabaseConfig().to_dict()
    
    try:
        conn = pymysql.connect(
            **config_dict,
            cursorclass=pymysql.cursors.DictCursor
        )
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)
