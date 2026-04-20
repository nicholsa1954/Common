from contextlib import contextmanager

@contextmanager
def timer():
    """
    ###usage:
    ###with timer():
        # code to time
    """
    import time
    start = time.time()
    yield
    end = time.time()
    print(f"Execution time: {end - start:.4f}s")