python 3.5之后的版本，如果报错
```
>>> from lxml import etree
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: DLL load failed while importing etree: 找不到指定的模块。
```
请更新lxml包（具体原因可能是你的lxml是在pycharm里下载的）
```
pip install --upgrade lxml
```


# SouBaiduPan-master

# 百度网盘搜索工具

## 实现功能：搜索百度网盘资源，自动抓取链接和密码，并可以在浏览器中批量打开。

#### 使用方法介绍：

参考[notebook](https://github.com/acgmusic/SouBaiduPan-master/blob/main/example/tutorial.ipynb)

1. 安装**SouBaiduPan**
   
    ```cmd
    pip install SouBaiduPan
    ```

1. 从`SouBaiduPan`导入`searcher`，并创建搜索器对象。初始化时，需要设定的参数包括：`搜索关键词`、`最大搜索页数`。其中搜索关键词建议在后面加上"网盘"，可以提高成功率；最大搜索页数建议选择20以内，设置太大的话可能会触发百度的验证码机制，导致无法继续爬取。

    ```python
    from SouBaiduPan import searcher

    keywords = "月球陨落 网盘"

    S = searcher.BaiduPanSearcher(keywords=keywords, max_page_nums=20)
    ```

1. 设置浏览器cookie。以Chrome浏览器为例，首先需要先在浏览器内打开[百度](https://www.baidu.com/)，然后在空白处`右键`->`检查`，在调出来的界面的上方，点击`Network`标签，然后刷新网页，此时会刷新出很多请求信息，拉到最上面，找到`www.baidu.com`的请求，单击点一下，右边会跳出一个边栏，确保在边栏上方选择的是`Headers`标签(默认就是，所以不要动就行)，然后找到`Cookie`对应的一长串的神秘代码，复制下来就行了。然后像下面这样进行设置：
    ```pythno
    S.set_cookie('请在这里输入你的cookie')
    ```

1. 执行下方代码，即可开始搜索。如果需要**在浏览器中自动打开搜索到的网盘链接**，请务必下载Chrome浏览器自动化测试驱动，方法请参考: https://zhuanlan.zhihu.com/p/373688337

   一些参数解释：

    `show`: 打印搜索到的链接，建议勾选。

    `show_origin_url`: 是否显示所有度盘链接的原链接。但如果提取码没识别到，则一定会显示。

    `open_in_Chrome`: 自动在Chrome浏览器中打开所有链接。请务必先安装驱动程序。
    
    `save_json_path`: 保存为json文件的路径。建议用搜索词命名，文件后缀为.json
    
    ```pythno
    S.get_dupan_urls(
        show=True, 
        open_in_Chrome=True, 
        save_json_path=f"./{keywords}.json"
    )
    ```

1. 注意，搜索的结果是一个字典的列表。如果需要获取该列表，请执行：
   ```python
   S.show_dupan_urls()
   ```

1. `BaiduPanSearcher`对象一旦创建，无法修改搜索关键词以及最大搜索页面数。如果需要改变，请重新创建`BaiduPanSearcher`对象。在脚本被关闭之前，只需设置一次浏览器cookie即可。



