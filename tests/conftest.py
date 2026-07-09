import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _isolate_state_dbs(tmp_path):
    """全套件密闭:把 history_db / cache_db 的 DB_PATH 统一指到 tmp,
    没自己 patch 路径的测试(如 TestClient 打真实端点)也不再读写 ~/.vibe-manager
    下的真实生产库(曾往生产统计页写进过假数据)。

    另外 history_db._conn 把连接缓存在 thread-local:第一个建连接的测试之后,
    所有 DB_PATH 补丁都会被穿透。每个测试前后关掉缓存连接,让补丁真正生效。"""
    import vibe.history_db as hdb
    import vibe.cache_db as cdb

    def _close():
        conn = getattr(hdb._local, 'conn', None)
        if conn is not None:
            conn.close()
            hdb._local.conn = None

    _close()
    with patch.object(hdb, 'DB_PATH', tmp_path / 'history.db'), \
         patch.object(cdb, 'DB_PATH', tmp_path / 'cache.db'):
        yield
    _close()
