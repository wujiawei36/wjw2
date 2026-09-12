"""内存滑动窗口限频：按「维度键」计数，超限返回 retry 秒数。

设计说明：
- 纯内存实现，零数据库开销；PythonAnywhere 单 worker，进程内共享一致。
- 键形如 f'{slug}:key:{key_hash}' / f'{slug}:ip:{ip}'，由调用方构造。
- 惰性清理每个键的过期时间戳 + 后台线程定期清理空键，防内存膨胀。
- 进程重启后计数归零（可接受的取舍，与 users.middleware 的 ip_access_records 一致）。
"""
import threading
import time

_records = {}  # {key: [timestamp, ...]}
_lock = threading.Lock()


def _cleanup_loop():
    """后台线程：定期删除已清空的键，防止字典无限膨胀。"""
    while True:
        time.sleep(60)
        with _lock:
            for key in list(_records.keys()):
                if not _records[key]:
                    del _records[key]


_cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True)
_cleanup_thread.start()


def reset():
    """清空所有计数（仅用于测试，避免进程级状态在测试间串扰）。"""
    with _lock:
        _records.clear()


def allow(key, window, max_count):
    """滑动窗口限频。返回 (allowed: bool, retry_after: int)。

    retry_after 仅在超限时返回有效值（秒），供 429 响应的 Retry-After 头使用。
    """
    now = time.time()
    with _lock:
        times = [t for t in _records.get(key, []) if now - t < window]
        if len(times) >= max_count:
            _records[key] = times
            retry = int(window - (now - times[0])) + 1
            return False, retry
        times.append(now)
        _records[key] = times
        return True, 0
