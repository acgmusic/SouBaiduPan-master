from threading import Thread
from typing import *


# 定义一个MyThread线程类， 可以获取线程的return返回值
class MyThread(Thread):
    def __init__(self, func, args=()):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        Thread.join(self)  # 等待线程执行完毕
        try:
            return self.result
        except Exception:
            print("线程返回结果失败")
            return None


# 并行任务模板，可以用于需要汇总最终结果的情况
# 如果函数返回的结果是列表，需要把内层列表解包时，则可设置：unpacked=True
def res_pool_parallel(func, args_list: List[Tuple], unpacked=False):
    res_pool = []
    thread_pool = []
    for args in args_list:
        my_thread = MyThread(
            func,
            args,
        )
        my_thread.start()
        thread_pool.append(my_thread)
    for thread in thread_pool:
        res = thread.get_result()
        if unpacked:
            res_pool += res
        else:
            res_pool.append(res)
    return res_pool


