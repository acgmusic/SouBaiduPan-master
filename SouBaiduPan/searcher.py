import re
import requests
from lxml import etree
from urllib import parse
from requests.adapters import HTTPAdapter
from .thread_tools import res_pool_parallel
import json
from selenium.webdriver import Chrome

HEADERS_DEFAULT = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/100.0.4896.127 Safari/537.36",
}


class BaiduPanSearcher:
    def __init__(self, keywords, max_page_nums=20):
        self.headers = HEADERS_DEFAULT
        self.simple_headers = {'User-Agent': HEADERS_DEFAULT['User-Agent']}
        self.keywords = keywords
        self.max_page_nums = max_page_nums
        self._dupan_url_list = []

    def set_cookie(self, cookie: str):
        assert len(cookie) > 20
        self.headers['Cookie'] = cookie

    def set_user_agent(self, user_agent: str):
        self.headers['User-Agent'] = user_agent
        self.simple_headers = {'User-Agent': user_agent}

    def reset_headers(self):
        self.headers = HEADERS_DEFAULT
        self.simple_headers = {'User-Agent': HEADERS_DEFAULT['User-Agent']}

    # 获取网页源代码
    def get_page_text(self, url):
        assert len(url) > 4 and url[:4] == 'http', "there should be 'https://' before your url"
        session = requests.Session()
        session.mount('http://', HTTPAdapter(max_retries=3))  # 设置超时重试次数
        session.mount('https://', HTTPAdapter(max_retries=3))

        headers = self.headers

        try:
            # timeout=(连接超时, 读取超时)，其中读取超时默认是无限，这样会导致永远卡住
            response = session.get(url, timeout=(20, 30), headers=headers)
            response.encoding = response.apparent_encoding
            page_text = response.text
            return page_text
        except requests.exceptions.RequestException:
            print(f"链接超时 {url} ")
            return ''

    # 获取百度搜索结果链接的真实链接
    def get_real_url(self, v_url):
        headers = self.headers
        response = requests.get(v_url, headers=headers, allow_redirects=False)  # 不允许重定向
        if response.status_code == 302:  # 如果返回302，就从响应头获取真实地址
            real_url = response.headers.get('Location')
        else:  # 否则从返回内容中用正则表达式提取出来真实地址
            try:
                real_url = re.findall("URL='(.*?)'", response.text)[0]
            except IndexError:
                raise Exception(f"真实链接获取失败 {v_url}")
        return real_url

    def get_one_page_of_baidu(self, page_num):
        pn = str(page_num * 10)
        url = "https://www.baidu.com/s?wd=" + parse.quote(self.keywords) + "&pn=" + pn
        page_text = self.get_page_text(url)
        tree = etree.HTML(page_text)
        res = []
        res += tree.xpath("//div[@id='content_left']/div//h3/a/@href")
        res += tree.xpath("//div[@id='content_left']/div//h4/a/@href")
        outer_chains = []
        for link in res:
            if "www.baidu.com/link" in link:
                outer_chains.append(link)
        return outer_chains

    def get_pages_of_baidu(self):
        fake_url_list = res_pool_parallel(
            self.get_one_page_of_baidu,
            [(i,) for i in range(self.max_page_nums)],
            unpacked=True
        )
        true_url_list = res_pool_parallel(
            self.get_real_url,
            [(fake_url,) for fake_url in fake_url_list]
        )
        return true_url_list

    def get_state_of_dupan_url(self, dupan_url):
        """
        返回值:0表示链接无效，1表示需要密码，2表示可直接访问
        """
        print(f"正在验证网盘链接 {dupan_url} ")
        page_text = self.get_page_text(dupan_url)
        patterns = [
            r"此链接分享内容可能因为涉及侵权、色情、反动、低俗等信息",
            r"分享的文件已经被取消了",
            r"链接错误没找到文件",
            r"你所访问的页面不存在了",
            r"分享的文件已经被删除",
            r"该共享文件夹已失效",
            r"该分享文件已过期",
        ]
        for ptn in patterns:
            if re.search(ptn, page_text) is not None:
                return 0
        if re.search(r"请输入提取码", page_text) is not None:
            return 1
        return 2

    def _find_data_url_and_pwd_in_rawtext(self, original_url):
        url_pattern = r"pan.baidu.com/s/[\w\-]+"
        pwd_pattern = r"(提取码|password|pwd|密码)(&nbsp;|\s)*([:：\s])(&nbsp;|\s)*(\w{4})"
        print(f"正在访问 {original_url} ")
        text = self.get_page_text(original_url)
        if not text:
            return []
        url_dicts = []
        # 先找出所有的链接，同时记录下链接的位置，方便后续寻找提取码
        cur = 0
        while cur < len(text):
            matcher = re.search(url_pattern, text[cur:])
            if matcher is None:
                break
            else:
                end = matcher.end()
                url = matcher.group()
                cur += end
                url_dicts.append({'url': 'https://' + url, 'end': cur})

        # 寻找提取码
        for i in range(len(url_dicts)):
            # url = url_dicts[i]['url']
            end = url_dicts[i]['end']
            if i == len(url_dicts) - 1:
                end_next = len(text)
            else:
                end_next = url_dicts[i + 1]['end']
            matcher = re.search(pwd_pattern, text[end:end_next])
            if matcher is None:
                pwd = ""
            else:
                pwd = matcher.group()[-4:]
            url_dicts[i]['pwd'] = pwd

        # 去除重复链接（优先保留有提取码的）
        for i in range(len(url_dicts)):
            url = url_dicts[i]['url']
            pwd = url_dicts[i]['pwd']
            if pwd:
                for j in range(len(url_dicts)):
                    if url_dicts[j]['url'] == url:
                        url_dicts[j]['pwd'] = pwd
        res_list = [
            {'url': info[0], 'pwd': info[1], 'original_url': original_url}
            for info in set(
                [(url_dict['url'], url_dict['pwd']) for url_dict in url_dicts]
            )
        ]
        for res in res_list:
            res['state'] = self.get_state_of_dupan_url(res['url'])
        return res_list

    def get_dupan_urls(self,
                       show=True,
                       show_origin_url=False,
                       open_in_Chrome=False,
                       save_json_path=None
                       ):
        """
        :show: 是否打印所有链接
        :show_origin_url: 是否显示所有度盘链接的原链接。但如果提取码没识别到，则一定会显示
        :open_in_Chrome: 是否在Chrome浏览器里打开所有有效地百度链接。要求必须安装Chrome的自动化测试驱动，参考：
        https://zhuanlan.zhihu.com/p/373688337
        :save_json_path: 保存为json文件的路径。建议用搜索词命名，文件后缀为.json
        """
        if not self._dupan_url_list:
            url_list = self.get_pages_of_baidu()
            dupan_url_list = res_pool_parallel(
                self._find_data_url_and_pwd_in_rawtext,
                [(url,) for url in url_list],
                unpacked=True
            )
            self._dupan_url_list = dupan_url_list

        if save_json_path is not None:
            with open(save_json_path, 'w', encoding="utf-8") as f:
                f.write(json.dumps(self._dupan_url_list))

        if show:
            print("=" * 40, " 有效链接 ", "=" * 40)
            for url_info in self._dupan_url_list:
                if (url_info['state'] == 2) or (url_info['state'] == 1 and url_info['pwd']):
                    print("_" * 60)
                    print("链接: ", url_info['url'])
                    if url_info['pwd']:
                        print("提取码: ", url_info['pwd'])
                    if show_origin_url:
                        print("原网页: ", url_info['original_url'])
            print("=" * 40, " 需自行查找提取码 ", "=" * 40, '\n')
            for url_info in self._dupan_url_list:
                if url_info['state'] == 1 and (not url_info['pwd']):
                    print("_" * 60)
                    print("链接: ", url_info['url'])
                    print("提取码: ", "未匹配成功，请点击原网页查找")
                    print("原网页: ", url_info['original_url'])

        if open_in_Chrome:
            self._driver = Chrome()
            full_url_list = []
            for url_info in self._dupan_url_list:
                if url_info['state'] == 0:
                    continue
                elif url_info['state'] == 1:
                    if url_info['pwd']:
                        url_full = url_info['url'] + "?pwd=" + url_info['pwd']
                    else:
                        continue
                else:
                    url_full = url_info['url']
                full_url_list.append(url_full)
            if full_url_list:
                self._driver.get(full_url_list[0])
                res_pool_parallel(
                    self._driver.execute_script,
                    [(f"window.open('{full_url}')",) for full_url in full_url_list[1:]]
                )

    def show_dupan_urls(self):
        return self._dupan_url_list


if __name__ == '__main__':
    searcher = BaiduPanSearcher("食神 网盘", 3)
    searcher.get_dupan_urls(show=True, open_in_Chrome=True, save_json_path="../test/test.json")
