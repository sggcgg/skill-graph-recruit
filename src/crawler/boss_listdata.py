import os
import csv
import json
import time
import random
import traceback
from loguru import logger
from datetime import datetime
from DrissionPage import ChromiumOptions, WebPage


class BossZhipinSpider(object):
    """BOSS直聘职位爬虫 - 简化版本（测试阶段）"""
    
    def __init__(self):
        self.logger = logger
        self.logger.add(
            "logs/boss_spider_{time}.log",
            rotation="500 MB",
            retention="10 days",
            level="INFO"
        )
        
        # 爬虫配置
        self.max_jobs_per_keyword = 50  # 每个关键词最多抓取的职位数
        self.page_delay_min = 2  # 页面切换最小延迟（秒）
        self.page_delay_max = 5  # 页面切换最大延迟（秒）
        
        # 数据存储配置
        self.data_dir = "data/boss_jobs"
        os.makedirs(self.data_dir, exist_ok=True)
        
    def human_like_delay(self, min_seconds=1, max_seconds=3):
        """模拟人类操作延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def random_scroll(self, page):
        """随机滚动页面，模拟人类浏览行为"""
        try:
            scroll_times = random.randint(2, 4)
            for _ in range(scroll_times):
                scroll_distance = random.randint(300, 800)
                page.run_js(f"window.scrollBy(0, {scroll_distance});")
                self.human_like_delay(0.5, 1.5)
                
            # 有时候向上滚动一点
            if random.random() > 0.7:
                page.run_js(f"window.scrollBy(0, -{random.randint(100, 300)});")
                self.human_like_delay(0.5, 1)
        except Exception as e:
            self.logger.warning(f"滚动页面失败: {e}")
    
    def init_browser(self):
        """初始化浏览器 - 无痕模式 + 反检测配置"""
        try:
            self.logger.info("正在初始化浏览器（无痕模式）...")
            
            # 配置浏览器选项
            co = ChromiumOptions()
            
            # ========== 无痕模式 ==========
            co.incognito()  # 启用无痕模式
            self.logger.info("✓ 已启用无痕模式")
            
            # ========== 反自动化检测 ==========
            # 关键！隐藏所有自动化相关的信息栏和警告
            co.set_argument('--disable-infobars')  # 禁用信息栏（隐藏所有顶部警告）
            
            # 排除启用自动化的标志
            co.set_argument('--exclude-switches', 'enable-automation')
            
            # 禁用自动化扩展
            co.set_argument('--disable-extensions')
            
            # 移除 webdriver 标志（通过pref设置，不会触发警告）
            co.set_pref('excludeSwitches', ['enable-automation', 'enable-logging'])
            co.set_pref('useAutomationExtension', False)
            
            # 实验性功能：通过实验性选项禁用自动化检测（不会触发警告）
            co.set_argument('--enable-features=NetworkService,NetworkServiceInProcess')
            co.set_argument('--disable-features=IsolateOrigins,site-per-process')
            
            # ========== 性能与稳定性 ==========
            # 注意：--no-sandbox 会触发警告，但在某些环境下是必需的
            # 如果不需要沙箱模式，可以注释掉下面这行
            # co.set_argument('--no-sandbox')
            
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-gpu')  # 禁用GPU加速，提高稳定性
            
            # 禁用Chrome的各种警告和提示
            co.set_argument('--disable-popup-blocking')  # 禁用弹窗拦截
            co.set_argument('--disable-notifications')  # 禁用通知
            
            # ========== 窗口设置 ==========
            co.set_argument('--window-size=1920,1080')
            co.set_argument('--start-maximized')  # 启动时最大化
            
            # ========== User-Agent 设置 ==========
            # 使用最新的Chrome User-Agent
            co.set_user_agent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            )
            
            # ========== 其他反检测设置 ==========
            # 禁用图片加载（可选，提高速度但可能影响某些检测）
            # co.set_argument('--blink-settings=imagesEnabled=false')
            
            # 禁用通知
            co.set_pref('profile.default_content_setting_values.notifications', 2)
            
            # 禁用密码保存提示
            co.set_pref('credentials_enable_service', False)
            co.set_pref('profile.password_manager_enabled', False)
            
            # 语言设置
            co.set_pref('intl.accept_languages', 'zh-CN,zh,en-US,en')
            
            # 隐藏自动化信息栏（关键配置）
            co.set_pref('profile.default_content_settings.popups', 0)
            co.set_pref('profile.default_content_settings.notifications', 2)
            
            # ========== 创建浏览器实例 ==========
            page = WebPage(chromium_options=co)
            
            # ========== JavaScript反检测注入 ==========
            # 强化版反检测脚本 - 一次性注入所有必要的伪装
            page.run_js('''
                // 1. 移除webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // 2. 伪装plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                    configurable: true
                });
                
                // 3. 伪装languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
                    configurable: true
                });
                
                // 4. 伪装Chrome对象
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // 5. 移除automation相关属性
                delete navigator.__proto__.webdriver;
                
                // 6. 伪装权限查询
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            ''')
            
            self.logger.info("✓ 浏览器初始化成功（已配置反检测）")
            self.logger.info("✓ User-Agent: Chrome/131.0.0.0")
            
            return page
            
        except Exception as e:
            self.logger.error(f"浏览器初始化失败: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def wait_for_login(self, page, wait_seconds=60):
        """
        等待用户手动扫码登录
        
        Args:
            page: 浏览器页面对象
            wait_seconds: 等待时间（秒）
        """
        self.logger.info("=" * 60)
        self.logger.info(f"请在 {wait_seconds} 秒内完成扫码登录!")
        self.logger.info("=" * 60)
        
        # 倒计时显示
        for remaining in range(wait_seconds, 0, -10):
            self.logger.info(f"⏰ 剩余时间: {remaining} 秒...")
            time.sleep(10)
        
        self.logger.info("✓ 登录等待时间结束")
        self.human_like_delay(2, 3)
    
    def parse_job_list(self, page):
        """
        解析职位列表页面
        
        Returns:
            list: 职位数据列表
        """
        jobs = []
        
        try:
            # 等待页面加载
            page.wait.doc_loaded(timeout=10)
            self.human_like_delay(2, 3)
            

            # 这里需要根据实际的HTML结构来编写选择器
            # 示例代码（需要根据实际情况修改）：
            
            # 查找所有职位卡片
            job_cards = page.eles('css:.job-card-wrapper')  # 示例选择器，需要根据实际修改
            
            if not job_cards:
                self.logger.warning("未找到职位卡片元素")
                return jobs
            
            self.logger.info(f"找到 {len(job_cards)} 个职位卡片")
            
            for idx, card in enumerate(job_cards, 1):
                try:

                    # 以下是示例代码，需要根据BOSS直聘实际结构修改
                    
                    job_data = {
                        'job_title': self.safe_get_text(card, '.job-title'),  # 示例
                        'company_name': self.safe_get_text(card, '.company-name'),  # 示例
                        'salary': self.safe_get_text(card, '.salary'),  # 示例
                        'location': self.safe_get_text(card, '.job-area'),  # 示例
                        'experience': self.safe_get_text(card, '.job-experience'),  # 示例
                        'education': self.safe_get_text(card, '.job-degree'),  # 示例
                        'job_tags': self.safe_get_text(card, '.tag-list'),  # 示例
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    jobs.append(job_data)
                    self.logger.debug(f"解析职位 {idx}: {job_data.get('job_title', 'Unknown')}")
                    
                except Exception as e:
                    self.logger.warning(f"解析第 {idx} 个职位卡片失败: {e}")
                    continue
            
            self.logger.info(f"✓ 成功解析 {len(jobs)} 个职位")
            
        except Exception as e:
            self.logger.error(f"解析职位列表失败: {e}")
            self.logger.error(traceback.format_exc())
        
        return jobs
    
    def safe_get_text(self, element, selector):
        """安全地获取元素文本"""
        try:
            target = element.ele(selector)
            if target:
                return target.text.strip()
        except:
            pass
        return ""
    
    def save_to_csv(self, jobs, keyword):
        """
        将职位数据保存到CSV文件
        
        Args:
            jobs: 职位数据列表
            keyword: 搜索关键词
        """
        if not jobs:
            self.logger.warning("没有数据需要保存")
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.data_dir}/boss_{keyword}_{timestamp}.csv"
            
            # 获取所有字段名
            fieldnames = list(jobs[0].keys())
            
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(jobs)
            
            self.logger.info(f"✓ 数据已保存到: {filename}")
            self.logger.info(f"✓ 共保存 {len(jobs)} 条职位数据")
            
        except Exception as e:
            self.logger.error(f"保存CSV文件失败: {e}")
            self.logger.error(traceback.format_exc())
    
    def save_to_json(self, jobs, keyword):
        """
        将职位数据保存到JSON文件
        
        Args:
            jobs: 职位数据列表
            keyword: 搜索关键词
        """
        if not jobs:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.data_dir}/boss_{keyword}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✓ JSON数据已保存到: {filename}")
            
        except Exception as e:
            self.logger.error(f"保存JSON文件失败: {e}")
    
    def scroll_to_bottom(self, page, scroll_times=35):
        """
        逐步下滑到底部，控制速度和频率避免风控
        
        Args:
            page: 浏览器页面对象
            scroll_times: 下滑次数，默认35次
        """
        try:
            self.logger.info(f"开始下滑页面，共 {scroll_times} 次...")
            
            for i in range(scroll_times):
                # 每次下滑的距离稍有变化，更像人类行为
                scroll_distance = random.randint(400, 600)
                
                # 执行下滑
                page.run_js(f"window.scrollBy(0, {scroll_distance});")
                
                self.logger.info(f"✓ 第 {i+1}/{scroll_times} 次下滑完成")
                
                # 控制下滑速度，避免风控
                # 每次下滑后随机等待 1.5-3 秒
                delay = random.uniform(1.5, 3.0)
                self.logger.debug(f"等待 {delay:.2f} 秒后继续...")
                time.sleep(delay)
                
                # 每隔几次下滑，停顿稍长时间，模拟人类阅读
                if (i + 1) % 5 == 0:
                    extra_delay = random.uniform(2, 4)
                    self.logger.info(f"第 {i+1} 次下滑完成，额外停顿 {extra_delay:.2f} 秒...")
                    time.sleep(extra_delay)
            
            self.logger.info("✓ 页面下滑完成，已到达底部")
            
        except Exception as e:
            self.logger.error(f"下滑页面失败: {e}")
            self.logger.error(traceback.format_exc())
    
    def search_keyword(self, page, keyword):
        """
        搜索关键词并抓取职位数据
        
        Args:
            page: 浏览器页面对象
            keyword: 搜索关键词
        
        Returns:
            list: 所有抓取到的职位数据
        """
        all_jobs = []
        
        try:
            self.logger.info(f"{'='*60}")
            self.logger.info(f"开始搜索关键词: {keyword}")
            self.logger.info(f"{'='*60}")
            
            # ========== 步骤1: 启动网络监听 ==========
            # ⚠️ 重要：必须在搜索之前启动监听，否则会漏掉第一页数据
            # 监听BOSS直聘职位列表API
            target_packet_name = 'wapi/zpgeek/search/joblist'
            
            self.logger.info(f"启动网络监听，目标包: {target_packet_name}")
            
            # 监听joblist接口
            page.listen.start(target_packet_name)
            self.logger.info("✓ 监听已启动")
            
            # ========== 步骤2: 定位搜索框 ==========
            # 使用xpath定位搜索框 - 通过placeholder属性定位
            search_box_selector = 'xpath://input[@placeholder="搜索职位、公司"]'
            
            self.logger.info("正在定位搜索框...")
            search_box = page.ele(search_box_selector)
            
            if not search_box:
                self.logger.error(f"未找到搜索框: {search_box_selector}")
                page.listen.stop()  # 记得停止监听
                return all_jobs
            
            # 清空搜索框并输入关键词
            search_box.clear()
            self.human_like_delay(0.5, 1)
            
            # 模拟人类输入，逐个字符输入
            self.logger.info(f"正在输入关键词: {keyword}")
            for char in keyword:
                search_box.input(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            self.human_like_delay(1, 2)
            
            # ========== 步骤3: 按回车提交搜索（会触发第一页数据加载）==========
            self.logger.info("按回车提交搜索...")
            search_box.input('\n')
            
            # 等待搜索结果加载
            self.logger.info("等待搜索结果加载（监听会捕获第一页数据包）...")
            self.human_like_delay(3, 5)
            page.wait.doc_loaded(timeout=10)
            
            # ========== 步骤4: 下滑页面触发更多数据加载 ==========
            self.logger.info("开始下滑页面触发更多数据加载...")
            self.scroll_to_bottom(page, scroll_times=5)
            
            # ========== 步骤5: 获取监听到的数据包 ==========
            self.logger.info("等待并获取数据包...")
            time.sleep(3)  # 等待最后的请求完成
            
            # 获取所有监听到的数据包（重要：必须在停止监听之前获取）
            try:
                self.logger.info("正在提取数据包...")
                
                # 使用wait()方法获取数据包，设置timeout避免无限等待
                packets = []
                packet_count = 0
                
                # 持续获取数据包，直到超时（没有新数据）
                while True:
                    try:
                        # 等待下一个数据包，超时时间1秒
                        packet = page.listen.wait(timeout=1)
                        
                        if packet:
                            packet_count += 1
                            packets.append(packet)
                            self.logger.debug(f"提取第 {packet_count} 个数据包")
                        else:
                            # 没有更多数据包
                            self.logger.info("没有更多数据包")
                            break
                            
                        # 安全限制：最多获取100个包
                        if packet_count >= 100:
                            self.logger.warning("数据包数量达到100，停止提取")
                            break
                            
                    except Exception as e:
                        # 超时或其他异常，表示没有更多数据
                        if "timeout" in str(e).lower() or "超时" in str(e):
                            self.logger.info(f"数据包获取完成（超时）")
                        else:
                            self.logger.warning(f"提取数据包异常: {e}")
                        break
                
            except Exception as e:
                self.logger.error(f"获取数据包时出错: {e}")
                self.logger.error(f"错误详情: {traceback.format_exc()}")
                packets = []
            
            # 停止监听（在获取数据之后）
            try:
                self.logger.info("停止监听...")
                page.listen.stop()
            except Exception as e:
                self.logger.warning(f"停止监听时出错: {e}")
            
            # 统计和显示结果
            if packets:
                self.logger.info(f"✓ 成功捕获 {len(packets)} 个数据包")
            else:
                self.logger.warning(f"未捕获到目标数据包: {target_packet_name}")
                self.logger.info("提示：请检查网络请求是否正常，或尝试增加等待时间")
            
            # ========== 步骤6: 打印抓取到的数据 ==========
            if packets:
                for idx, packet in enumerate(packets, 1):
                    self.logger.info(f"\n{'='*60}")
                    self.logger.info(f"数据包 {idx}:")
                    self.logger.info(f"{'='*60}")
                    
                    # 打印响应数据
                    try:
                        response_body = packet.response.body
                        
                        # 如果是JSON格式，格式化打印
                        if isinstance(response_body, (dict, list)):
                            self.logger.info(json.dumps(response_body, ensure_ascii=False, indent=2))
                        else:
                            # 尝试解析JSON字符串
                            try:
                                data = json.loads(response_body)
                                self.logger.info(json.dumps(data, ensure_ascii=False, indent=2))
                            except:
                                self.logger.info(response_body)
                        
                        # 保存数据（测试阶段）
                        all_jobs.append(response_body)
                        
                    except Exception as e:
                        self.logger.warning(f"解析数据包 {idx} 失败: {e}")
                        self.logger.warning(f"错误详情: {traceback.format_exc()}")
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"关键词 '{keyword}' 抓取完成")
            self.logger.info(f"{'='*60}")
            
            # ========== 测试阶段：暂停后续处理逻辑 ==========
            self.logger.info("⚠️  测试模式：暂停后续处理逻辑")
            
        except Exception as e:
            self.logger.error(f"搜索关键词 '{keyword}' 时出错: {e}")
            self.logger.error(traceback.format_exc())
        
        return all_jobs
    
    def run(self, keywords):
        """
        主运行函数
        
        Args:
            keywords: 关键词列表，例如 ['Python', 'Java', '数据分析']
        """
        page = None
        
        try:

            page = self.init_browser()
            
            # 2. 访问BOSS直聘首页
            self.logger.info("正在访问BOSS直聘...")
            page.get('https://www.zhipin.com/web/user/?ka=header-login')
            page.wait.doc_loaded(timeout=15)
            self.human_like_delay(2, 3)
            
            # 3. 等待用户验证码登录（60秒）
            self.wait_for_login(page, wait_seconds=40)
            
            # 4. 访问职位列表页面
            self.logger.info("正在访问职位列表页面...")
            page.get('https://www.zhipin.com/web/geek/jobs?city=100010000')
            page.wait.doc_loaded(timeout=15)
            self.human_like_delay(2, 3)
            self.logger.info("✓ 职位列表页面加载完成")

            # 5. 循环处理每个关键词
            for idx, keyword in enumerate(keywords, 1):
                self.logger.info(f"\n正在处理第 {idx}/{len(keywords)} 个关键词: {keyword}")
                
                # 搜索关键词并抓取数据
                jobs = self.search_keyword(page, keyword)
                
                # 测试阶段：只打印数据，不保存
                self.logger.info(f"\n关键词 '{keyword}' 共抓取到 {len(jobs)} 条数据")
                
                # 关键词之间的延迟
                if idx < len(keywords):
                    delay = random.uniform(5, 10)
                    self.logger.info(f"等待 {delay:.2f} 秒后处理下一个关键词...")
                    time.sleep(delay)
            
            self.logger.info("\n" + "="*60)
            self.logger.info("所有关键词处理完成！")
            self.logger.info("="*60)
            
        except KeyboardInterrupt:
            self.logger.warning("\n用户中断程序")
        except Exception as e:
            self.logger.error(f"程序运行出错: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            # 关闭浏览器
            if page:
                self.logger.info("正在关闭浏览器...")
                try:
                    page.quit()
                    self.logger.info("✓ 浏览器已关闭")
                except:
                    pass
                



if __name__ == "__main__":
    # 创建爬虫实例
    spider = BossZhipinSpider()
    
    # 定义要搜索的关键词列表
    keywords = [
        'Python',
        'Java',

    ]
    
    # 运行爬虫
    spider.run(keywords)
