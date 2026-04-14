"""
数据库连接模块
"""
import json
import pymysql
from pathlib import Path


class DatabaseConfig:
    """数据库配置"""
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self):
        config_path = Path(__file__).parent.parent / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return data.get('database', {})
        return {'enabled': False}
    
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


# 全局配置
_config = DatabaseConfig()


def get_db():
    """获取数据库连接（每次创建新连接）"""
    if not _config.enabled:
        return None
    
    try:
        conn = pymysql.connect(
            host=_config.host,
            port=_config.port,
            user=_config.user,
            password=_config.password,
            database=_config.database,
            charset=_config.charset,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10
        )
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None


class DatabaseConnection:
    """兼容类"""

    config = _config
    
    @staticmethod
    def get_connection():
        return get_db()


def test_connection():
    """测试数据库连接"""
    conn = get_db()
    if conn:
        conn.close()
        return True, None
    return False, 'Database connection failed'
