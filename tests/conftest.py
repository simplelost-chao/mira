import pytest


@pytest.fixture(autouse=True)
def _reset_history_db_conn():
    """history_db._conn 把连接缓存在 thread-local:第一个建连接的测试之后,
    所有 DB_PATH 补丁都被穿透(全量跑时曾串到真实生产库,写进过假数据)。
    每个测试前后关掉缓存连接,让各自的 DB_PATH 补丁真正生效。"""
    import vibe.history_db as hdb

    def _close():
        conn = getattr(hdb._local, 'conn', None)
        if conn is not None:
            conn.close()
            hdb._local.conn = None

    _close()
    yield
    _close()
