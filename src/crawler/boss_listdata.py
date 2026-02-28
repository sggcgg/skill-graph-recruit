import os
import csv
import json
import time
import random
import traceback
import uuid
from loguru import logger
from datetime import datetime
from DrissionPage import ChromiumOptions, WebPage

# 确保工作目录为项目根目录
# 无论从哪里运行此脚本，都能正确找到配置文件
# 获取脚本所在目录的父目录的父目录（即项目根目录）
# src/crawler/boss_listdata.py -> src/crawler -> src -> 项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


class BossZhipinSpider(object):
    """BOSS直聘职位爬虫 - 简化版本（测试阶段）"""
    
    VERSION = "1.6.1"  # 版本号（智能检测底部 + 性能优化 + 风控保护优化）
    
    def __init__(self):
        self.logger = logger
        # 确保日志目录存在
        log_dir = os.path.join(PROJECT_ROOT, "src", "crawler", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger.add(
            os.path.join(log_dir, "boss_spider_{time}.log"),
            rotation="500 MB",
            retention="10 days",
            level="INFO"
        )
        
        # ========== 爬虫配置（优化版 v1.4）==========
        # 下滑次数配置：Boss直聘每个关键词约300条数据，下滑90次可获取更多数据
        self.scroll_times_per_keyword = 90  # 每个关键词下滑次数（90次获取更全面数据）
        self.page_delay_min = 2  # 页面切换最小延迟（秒）
        self.page_delay_max = 5  # 页面切换最大延迟（秒）
        
        # ========== 风控配置（保守版，降低封号风险）==========
        self.enable_anti_detection = True  # 是否启用反检测增强
        self.task_interval_min = 5    # 任务间最小间隔（秒）
        self.task_interval_max = 10   # 任务间最大间隔（秒）
        self.long_break_interval = 10 # 每10个任务强制长休息一次（更频繁）
        self.long_break_min = 15      # 长休息最小时间（秒）
        self.long_break_max = 25      # 长休息最大时间（秒）
        
        # ========== 性能优化配置 ==========
        self.fast_scroll_mode = True  # 启用快速滚动模式
        self.batch_process_packets = True  # 启用批量处理数据包
        
        # ========== 风控保护配置 ==========
        self.max_consecutive_failures = 5  # 连续失败次数上限（触发自动停止）
        self.consecutive_failures = 0  # 当前连续失败次数
        self.enable_risk_detection = True  # 启用风控检测
        
        # ========== 数据存储配置 ==========
        # 原始数据保存目录：data/raw/ （直接保存到raw目录）
        self.data_dir = os.path.join(PROJECT_ROOT, "data", "raw")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 城市数据文件路径缓存：{城市名: 文件路径}
        self.city_files = {}
        # 城市已有job_id集合：{城市名: set(job_id1, job_id2, ...)}
        self.city_job_ids = {}
        # 城市职位数据内存缓存：{城市名: [job1, job2, ...]}
        # 避免每次关键词完成后重复从磁盘读取城市大文件（关键性能优化）
        self.city_data_cache = {}
        
        # ========== 断点续传配置 ==========
        # 进度文件保存路径
        self.progress_file = os.path.join(PROJECT_ROOT, "data", "crawler_progress.json")
        self.enable_resume = True  # 是否启用断点续传
        # 进度信息内存缓存，避免每个任务重复读写磁盘
        self._progress_cache = None
        
        # ========== 测试模式配置 ==========
        self.test_mode = False  # 是否为测试模式
        self.test_scroll_times = 5  # 测试模式下滑次数（正常55次，测试5次）
        
        # ========== 城市配置 ==========
        # 已抓取城市（第一批）
        self.cities_done = {
            '北京': '101010100',
            '上海': '101020100',
            '广州': '101280100',
            '深圳': '101280600',
            '杭州': '101210100',
            '成都': '101270100',
        }

        # 待抓取城市（第二批，按字母/拼音排序）
        self.cities_new = {
            '天津': '101030100',
            '重庆': '101040100',
            '哈尔滨': '101050100',
            '长春': '101060100',
            '大连': '101070200',
            '呼和浩特': '101080100',
            '太原': '101100100',
            '西安': '101110100',
            '兰州': '101160100',
            '郑州': '101180100',
            '开封': '101180800',
            '南京': '101190100',
            '无锡': '101190200',
            '苏州': '101190400',
            '扬州': '101190600',
            '合肥': '101220100',
            '芜湖': '101220300',
            '福州': '101230100',
            '厦门': '101230200',
            '南昌': '101240100',
            '长沙': '101250100',
            '常德': '101250600',
            '贵阳': '101260100',
            '武汉': '101200100',
            '佛山': '101280800',
            '东莞': '101281600',
            '海口': '101310100',
        }

        # 当前抓取任务用的城市（由菜单选择决定）
        self.cities = self.cities_done  # 默认兼容原有逻辑
        
        # ========== 关键词配置 ==========
        # 从 data/crawl_keywords.json 加载关键词列表
        self.keywords_config_file = os.path.join(PROJECT_ROOT, "data", "crawl_keywords.json")
        self.all_keywords = []  # 所有关键词（岗位类型 + 技能关键词）
        self.load_keywords()
        
    def load_keywords(self):
        """
        从 data/crawl_keywords.json 加载关键词列表
        
        关键词来源：由 scripts/generate_crawl_keywords.py 从技能词典自动生成
        包含：
          - job_type_keywords: 岗位类型关键词（如"Python开发"、"算法工程师"）
          - skill_keywords: 技能关键词（如"Spring Boot"、"Vue"、"Redis"）
        
        预计数据量（多城市版本）：
          - 城市数量：6个（北京、上海、广州、深圳、杭州、成都）
          - 总关键词数：99个（已优化）
          - 每个城市每个关键词：约300条岗位
          - 理论总数：6 × 99 × 300 = 178,200条
          - 去重后：约106,920条（优秀级别）
        """
        try:
            if not os.path.exists(self.keywords_config_file):
                self.logger.warning(f"关键词配置文件不存在: {self.keywords_config_file}")
                self.logger.info(f"请先运行: python scripts/generate_crawl_keywords.py")
                self.logger.info(f"或检查文件是否存在于: {self.keywords_config_file}")
                self.all_keywords = []
                return
            
            with open(self.keywords_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载所有关键词（岗位类型 + 技能关键词）
            job_keywords = config.get('job_type_keywords', [])
            skill_keywords = config.get('skill_keywords', [])
            
            # 合并关键词列表
            self.all_keywords = job_keywords + skill_keywords
            
            self.logger.info(f"✓ 成功加载关键词配置文件")
            self.logger.info(f"  - 岗位类型关键词: {len(job_keywords)}个")
            self.logger.info(f"  - 技能关键词: {len(skill_keywords)}个")
            self.logger.info(f"  - 总关键词数: {len(self.all_keywords)}个")
            self.logger.info(f"  - 城市数量: {len(self.cities)}个")
            
            # 预估数据量（多城市）
            estimated_total = len(self.cities) * len(self.all_keywords) * 300
            estimated_after_dedup = int(estimated_total * 0.6)
            self.logger.info(f"  - 预计抓取: {estimated_total:,}条 (去重后约 {estimated_after_dedup:,}条)")
            
        except Exception as e:
            self.logger.error(f"加载关键词配置失败: {e}")
            self.logger.error(traceback.format_exc())
            self.all_keywords = []
    
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
    
    def simulate_human_interaction(self, page):
        """模拟人类交互行为（增强反检测）"""
        try:
            # 随机移动鼠标
            if random.random() > 0.5:
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                page.run_js(f"""
                    var evt = new MouseEvent('mousemove', {{
                        clientX: {x},
                        clientY: {y}
                    }});
                    document.dispatchEvent(evt);
                """)
                time.sleep(random.uniform(0.1, 0.3))
            
            # 偶尔向上滚动（模拟回看）
            if random.random() > 0.8:
                scroll_up = random.randint(200, 500)
                page.run_js(f"window.scrollBy(0, -{scroll_up});")
                time.sleep(random.uniform(1, 2))
                
        except Exception as e:
            self.logger.debug(f"模拟交互失败: {e}")
    
    # ========== 反检测资源池 ==========
    # 只使用 Windows + Chrome UA，与实际运行环境完全一致
    # 版本在最近几个主流版本之间轮换，避免固定版本被标记
    _UA_POOL = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6423.119 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.103 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.120 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.120 Safari/537.36',
    ]

    # 常见真实分辨率
    _WINDOW_SIZES = [
        (1920, 1080), (1920, 1080), (1920, 1080),  # 最常见，权重高
        (1440, 900), (1536, 864), (2560, 1440),
        (1366, 768), (1280, 800), (1600, 900),
    ]

    def _get_stealth_js(self) -> str:
        """生成高度拟真的反检测JS（Canvas/WebGL指纹随机化 + 真实plugins）"""
        # 随机Canvas噪声偏移量（每次启动不同）
        r_offset = random.randint(1, 8)
        g_offset = random.randint(1, 8)
        b_offset = random.randint(1, 8)

        return f'''
(function() {{
    // ===== 1. 彻底清除 webdriver 标志 =====
    // 同时覆盖 prototype 和实例，双重保障，防止任何访问路径返回 true
    try {{
        Object.defineProperty(Navigator.prototype, 'webdriver', {{
            get: () => undefined,
            configurable: true,
            enumerable: false
        }});
    }} catch(e) {{}}
    try {{
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
            configurable: true,
            enumerable: false
        }});
    }} catch(e) {{}}
    try {{ delete Navigator.prototype.webdriver; }} catch(e) {{}}
    try {{ delete navigator.__proto__.webdriver; }} catch(e) {{}}

    // ===== 2. 仿真 plugins =====
    try {{
        const pluginData = [
            {{ name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer',             description: 'Portable Document Format' }},
            {{ name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
            {{ name: 'Native Client',      filename: 'internal-nacl-plugin',             description: '' }},
        ];
        const pluginArray = pluginData.map(p => {{
            const plugin = Object.create(Plugin.prototype);
            Object.defineProperties(plugin, {{
                name:        {{ value: p.name,        enumerable: true }},
                filename:    {{ value: p.filename,    enumerable: true }},
                description: {{ value: p.description, enumerable: true }},
                length:      {{ value: 0,             enumerable: true }},
            }});
            return plugin;
        }});
        Object.defineProperty(navigator, 'plugins', {{
            get: () => Object.assign(pluginArray, {{
                length: pluginArray.length,
                item: i => pluginArray[i],
                namedItem: n => pluginArray.find(p => p.name === n) || null,
                refresh: () => {{}}
            }}),
            configurable: true
        }});
    }} catch(e) {{}}

    // ===== 3. 语言 =====
    try {{
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            configurable: true
        }});
    }} catch(e) {{}}

    // ===== 4. chrome 对象 =====
    try {{
        if (!window.chrome) {{
            window.chrome = {{
                app: {{ isInstalled: false }},
                runtime: {{}},
                csi: function() {{ return {{ startE: Date.now(), onloadT: Date.now() + 40, pageT: 1000 + Math.random()*500, tran: 15 }}; }},
                loadTimes: function() {{ return {{ commitLoadTime: Date.now()/1000 - 2, connectionInfo: 'h2', finishDocumentLoadTime: Date.now()/1000 - 0.5, finishLoadTime: Date.now()/1000 - 0.1, firstPaintTime: Date.now()/1000 - 1.5, navigationType: 'Other', wasNpnNegotiated: true }}; }},
            }};
        }}
    }} catch(e) {{}}

    // ===== 5. Canvas 指纹随机化 =====
    try {{
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {{
            if (type === 'image/png' && this.width > 16) {{
                const ctx = this.getContext('2d');
                if (ctx) {{
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        imageData.data[i]     = Math.min(255, imageData.data[i]     + {r_offset});
                        imageData.data[i + 1] = Math.min(255, imageData.data[i + 1] + {g_offset});
                        imageData.data[i + 2] = Math.min(255, imageData.data[i + 2] + {b_offset});
                    }}
                    ctx.putImageData(imageData, 0, 0);
                }}
            }}
            return origToDataURL.apply(this, arguments);
        }};
    }} catch(e) {{}}

    // ===== 6. WebGL 指纹随机化 =====
    try {{
        const _webglVendors = [
            ['Google Inc. (NVIDIA)', 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'],
            ['Google Inc. (Intel)',  'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)'],
            ['Google Inc. (AMD)',    'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)'],
            ['Google Inc. (NVIDIA)', 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)'],
            ['Google Inc. (Intel)',  'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)'],
        ];
        const _wgl = _webglVendors[{random.randint(0, 4)}];
        const getParamOrig = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return _wgl[0];
            if (parameter === 37446) return _wgl[1];
            return getParamOrig.call(this, parameter);
        }};
    }} catch(e) {{}}

    // ===== 7. 权限查询伪装 =====
    try {{
        const origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({{ state: Notification.permission }})
                : origQuery(parameters)
        );
    }} catch(e) {{}}

    // ===== 8. 隐藏 headless 特征（每个独立 try-catch） =====
    try {{ Object.defineProperty(navigator, 'maxTouchPoints',      {{ get: () => 0,                               configurable: true }}); }} catch(e) {{}}
    try {{ Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {random.choice([4, 8, 12, 16])}, configurable: true }}); }} catch(e) {{}}
    try {{ Object.defineProperty(navigator, 'deviceMemory',        {{ get: () => {random.choice([4, 8, 16])},     configurable: true }}); }} catch(e) {{}}
    try {{ Object.defineProperty(screen, 'colorDepth',             {{ get: () => 24,                              configurable: true }}); }} catch(e) {{}}
    try {{ Object.defineProperty(screen, 'pixelDepth',             {{ get: () => 24,                              configurable: true }}); }} catch(e) {{}}
}})();
'''

    def _save_cookies(self, page, filename='boss_cookies.json'):
        """保存登录 Cookie，下次直接复用，避免频繁扫码"""
        try:
            cookie_path = os.path.join(PROJECT_ROOT, 'data', filename)
            cookies = page.cookies()
            with open(cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)
            self.logger.info(f"✓ Cookie 已保存: {cookie_path}")
        except Exception as e:
            self.logger.warning(f"Cookie 保存失败: {e}")

    def _load_cookies(self, page, filename='boss_cookies.json'):
        """加载已保存的 Cookie，跳过登录流程"""
        try:
            cookie_path = os.path.join(PROJECT_ROOT, 'data', filename)
            if not os.path.exists(cookie_path):
                return False
            # Cookie 超过12小时则视为过期
            mtime = os.path.getmtime(cookie_path)
            if time.time() - mtime > 12 * 3600:
                self.logger.info("Cookie 已过期（>12小时），需要重新登录")
                return False
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            for cookie in cookies:
                try:
                    page.set.cookies(cookie)
                except Exception:
                    pass
            self.logger.info(f"✓ Cookie 加载成功（{len(cookies)} 条），尝试跳过登录")
            return True
        except Exception as e:
            self.logger.warning(f"Cookie 加载失败: {e}")
            return False

    def init_browser(self):
        """初始化浏览器 - 强化反检测配置（CDP注入，页面加载前生效）"""
        try:
            ua = random.choice(self._UA_POOL)
            win_w, win_h = random.choice(self._WINDOW_SIZES)
            self.logger.info(f"正在初始化浏览器... UA: {ua[:60]}...")
            self.logger.info(f"窗口大小: {win_w}x{win_h}")

            co = ChromiumOptions()

            # ========== 关键说明 ==========
            # 不使用 --disable-blink-features=AutomationControlled：
            #   该 flag 会让 Chrome 显示"不受支持的命令行标记"警告条，
            #   这个警告条本身就是一个明显的自动化特征，反而暴露身份。
            # 也不使用 --exclude-switches=enable-automation：
            #   DrissionPage 的 CDP 模式不依赖 --enable-automation，
            #   不需要排除它。
            # 反检测完全交给 CDP JS 注入（Page.addScriptToEvaluateOnNewDocument）
            # 和 run_js 双保险来实现。

            # ========== 让 Chrome 行为更接近普通用户 ==========
            co.set_argument('--no-first-run')
            co.set_argument('--no-default-browser-check')
            co.set_argument('--no-pings')

            # ========== 无痕模式 ==========
            co.incognito()

            # ========== 禁用扩展（无痕本就无扩展，加上避免系统级扩展干扰监听）==========
            co.set_argument('--disable-extensions')

            # ========== 稳定性参数 ==========
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-popup-blocking')
            co.set_argument('--disable-notifications')
            # 注意：不加 --disable-gpu，真实浏览器都有GPU加速

            # ========== 窗口设置（随机分辨率）==========
            co.set_argument(f'--window-size={win_w},{win_h}')

            # ========== 偏好设置 ==========
            # 注意：不用 co.set_user_agent()，改用后面的 CDP Emulation.setUserAgentOverride
            # co.set_user_agent 只改 navigator.userAgent，不改 navigator.userAgentData.brands
            # 两者不一致会被 BOSS 检测到
            co.set_pref('profile.default_content_setting_values.notifications', 2)
            co.set_pref('credentials_enable_service', False)
            co.set_pref('profile.password_manager_enabled', False)
            co.set_pref('intl.accept_languages', 'zh-CN,zh,en-US,en')

            # ========== 创建浏览器实例 ==========
            page = WebPage(chromium_options=co)

            # ========== 关键：用 CDP 在每个新页面加载【之前】注入反检测JS ==========
            # page.run_js() 是页面加载【之后】执行，那时候已经被检测了
            # Page.addScriptToEvaluateOnNewDocument 在 HTML 解析前就运行，彻底规避检测
            # 必须先 Page.enable，否则 addScriptToEvaluateOnNewDocument 在部分环境下无效
            try:
                page.run_cdp('Page.enable')
            except Exception:
                pass
            stealth_js = self._get_stealth_js()
            result = page.run_cdp('Page.addScriptToEvaluateOnNewDocument', source=stealth_js)
            self.logger.info(f"✓ CDP反检测注入成功: scriptId={result.get('identifier', 'ok')}")

            # ========== 用 CDP 同时覆盖 UA 和 userAgentData（两者必须一致）==========
            # co.set_user_agent 只改 navigator.userAgent，不改 userAgentData.brands
            # BOSS 会比对两者，不一致即判定为伪造 → 用 Emulation.setUserAgentOverride 一次解决
            try:
                # 先读取 Chrome 实际版本号，从真实 UA 中提取
                page.get('about:blank')
                real_ua = page.run_js('return navigator.userAgent') or ''
                self.logger.info(f"Chrome 实际 UA: {real_ua}")
                # 从实际 UA 提取版本，比如 "Chrome/131.0.6778.86" → "131"
                import re as _re
                _m = _re.search(r'Chrome/(\d+)', real_ua)
                chrome_ver = _m.group(1) if _m else '131'
                # 使用实际 UA（不改版本，只保证一致性）
                page.run_cdp('Emulation.setUserAgentOverride',
                    userAgent=real_ua,
                    platform='Win32',
                    acceptLanguage='zh-CN,zh,en-US,en',
                    userAgentMetadata={
                        'brands': [
                            {'brand': 'Google Chrome',  'version': chrome_ver},
                            {'brand': 'Chromium',       'version': chrome_ver},
                            {'brand': 'Not_A Brand',    'version': '24'},
                        ],
                        'fullVersionList': [
                            {'brand': 'Google Chrome',  'version': f'{chrome_ver}.0.0.0'},
                            {'brand': 'Chromium',       'version': f'{chrome_ver}.0.0.0'},
                            {'brand': 'Not_A Brand',    'version': '24.0.0.0'},
                        ],
                        'platform': 'Windows',
                        'platformVersion': '10.0.0',
                        'architecture': 'x86',
                        'model': '',
                        'mobile': False,
                        'bitness': '64',
                        'wow64': False,
                    }
                )
                self.logger.info(f"✓ UA 和 userAgentData 已同步 (Chrome/{chrome_ver})")
            except Exception as _e:
                self.logger.warning(f"UA/userAgentData 同步失败（使用默认）: {_e}")

            self.logger.info("✓ 浏览器初始化成功（CDP反检测已注入，页面加载前生效）")
            return page

        except Exception as e:
            self.logger.error(f"浏览器初始化失败: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def wait_for_login(self, page, wait_seconds=30):
        """
        等待用户手动扫码登录
        
        Args:
            page: 浏览器页面对象
            wait_seconds: 等待时间（秒）
        """
        self.logger.info("=" * 60)
        self.logger.info(f"请在 {wait_seconds} 秒内完成扫码登录!")
        self.logger.info("=" * 60)

        # 在等待过程中每隔10秒重新注入一次 webdriver 覆盖（防止BOSS页面的JS把它还原）
        _wd_patch = (
            "try { Object.defineProperty(navigator, 'webdriver', "
            "{get: () => undefined, configurable: true, enumerable: false}); } catch(e) {}"
        )

        # 倒计时显示（每轮检测并打印 webdriver + 当前 URL，用于排查是否被检测到）
        for remaining in range(wait_seconds, 0, -10):
            try:
                cur_url = page.url or ''
                wd_val  = page.run_js('return navigator.webdriver')
                wd_str  = repr(wd_val)
                status  = "✓ 隐藏成功" if not wd_val else "⚠️ 仍为 true！"
                self.logger.info(f"⏰ 剩余 {remaining}s | URL={cur_url[:60]} | webdriver={wd_str} {status}")
                if wd_val:
                    # webdriver 暴露，立刻重新注入
                    page.run_js(_wd_patch)
            except Exception as _e:
                self.logger.info(f"⏰ 剩余 {remaining}s（状态检测异常: {_e}）")
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
    
    def check_risk_control(self, page):
        """
        检测是否触发风控（验证码、登录过期等）
        
        检测内容：
          1. 验证码页面
          2. 登录过期
          3. 访问限制
          4. IP封禁
        
        Returns:
            tuple: (is_blocked, reason)
              - is_blocked: bool，True表示被风控
              - reason: str，风控原因
        """
        try:
            page_text = page.html
            page_url = page.url
            page_title = page.title
            
            # 检测1：验证码（优化：使用更精确的关键词，避免误判）
            # 优先检测中文提示（更准确）
            captcha_keywords_high_priority = [
                '请完成安全验证',
                '安全验证中',
                '滑动验证码',
                '点击完成验证',
                '请拖动滑块',
                '验证码验证'
            ]
            for keyword in captcha_keywords_high_priority:
                if keyword in page_text:
                    self.logger.warning(f"检测到高优先级验证码关键词: {keyword}")
                    return True, f"触发验证码: {keyword}"
            
            # 检测标题中的验证码提示
            if page_title and ('验证' in page_title or 'captcha' in page_title.lower()):
                self.logger.warning(f"检测到页面标题包含验证码: {page_title}")
                return True, f"页面标题包含验证码: {page_title}"
            
            # 检测URL中的验证码标识（更可靠）
            if 'captcha' in page_url.lower() or 'verify' in page_url.lower():
                self.logger.warning(f"检测到URL包含验证码标识: {page_url}")
                return True, f"URL包含验证码: {page_url}"
            
            # 检测2：登录过期（优化：排除正常的登录按钮）
            login_keywords = [
                '登录已过期',
                '需要重新登录',
                '请先登录后再',
                '登录状态失效'
            ]
            for keyword in login_keywords:
                if keyword in page_text:
                    self.logger.warning(f"检测到登录过期关键词: {keyword}")
                    return True, f"登录过期: {keyword}"
            
            # 检测3：访问限制
            limit_keywords = [
                '访问过于频繁',
                '请稍后再试',
                '系统繁忙',
                '访问受限',
                '操作太频繁',
                '请求过于频繁'
            ]
            for keyword in limit_keywords:
                if keyword in page_text:
                    self.logger.warning(f"检测到访问限制关键词: {keyword}")
                    return True, f"访问限制: {keyword}"
            
            # 检测4：异常跳转（如跳转到首页、错误页）
            # 优化：只检测明确的错误页面，排除正常首页
            if '/error' in page_url.lower() or page_url.endswith('/404') or page_url.endswith('/403'):
                self.logger.warning(f"检测到异常跳转: {page_url}")
                return True, f"异常跳转: {page_url}"
            
            return False, ""
            
        except Exception as e:
            self.logger.debug(f"风控检测失败: {e}")
            return False, ""
    
    def check_if_reached_bottom(self, page):
        """
        检测是否已到达页面底部
        
        检测方法：
          1. 检查是否出现"已经到底了"提示
          2. 检查滚动位置是否不再变化
          3. 检查是否有"没有更多数据"的标识
        
        Returns:
            bool: True表示已到底，False表示未到底
        """
        try:
            # 方法1：检查页面是否有"已经到底了"、"没有更多了"等提示
            bottom_texts = [
                '已经到底了',
                '没有更多了',
                '暂无更多职位',
                '已加载全部',
                '到底啦'
            ]
            
            page_text = page.html
            for text in bottom_texts:
                if text in page_text:
                    self.logger.info(f"✓ 检测到底部提示: {text}")
                    return True
            
            # 方法2：检查滚动位置
            scroll_info = page.run_js("""
                return {
                    scrollTop: document.documentElement.scrollTop,
                    scrollHeight: document.documentElement.scrollHeight,
                    clientHeight: document.documentElement.clientHeight
                };
            """)
            
            if scroll_info:
                scroll_top = scroll_info.get('scrollTop', 0)
                scroll_height = scroll_info.get('scrollHeight', 0)
                client_height = scroll_info.get('clientHeight', 0)
                
                # 如果滚动位置 + 可视高度 >= 总高度 - 100px，认为到底了
                if scroll_top + client_height >= scroll_height - 100:
                    self.logger.info(f"✓ 检测到页面底部（滚动位置）")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"检测底部失败: {e}")
            return False
    
    def scroll_to_bottom(self, page, scroll_times=55):
        """
        智能下滑策略 v1.6 - 更频繁底部检测 + 更大滚动步长
        
        优化点（相较 v1.5）：
          - 底部检测间隔：5次 → 3次（更早发现到底，节省无效滚动）
          - 单次滚动距离：500-800px → 600-1000px（步长更大，更快到底）
          - 额外停顿间隔：10-15次 → 12-18次（保留随机性同时减少停顿次数）
          - 保留全部风控保护：随机距离/延迟/偶发停顿
        
        性能估算（对比 v1.5）：
          - 更大步长：更早触底，平均节省 5-15 次滚动
          - 更频繁检测：触底后最多额外3次才停，而非最多5次
          - 综合节省：每关键词约 5-20 秒

        Args:
            page: 浏览器页面对象
            scroll_times: 最大下滑次数
        """
        try:
            self.logger.info(f"开始下滑页面，最多 {scroll_times} 次（智能检测模式 v1.6）...")

            last_scroll_top = 0
            no_change_count = 0

            for i in range(scroll_times):
                # 每3次检测一次是否到底（v1.5 是每5次，更早感知底部）
                if i > 0 and i % 3 == 0:
                    current_scroll_top = page.run_js("return document.documentElement.scrollTop;")

                    if current_scroll_top == last_scroll_top:
                        no_change_count += 1
                        self.logger.debug(f"滚动位置未变化（{no_change_count}次）")

                        if no_change_count >= 3:
                            early_stop_msg = f"✓ 检测到页面底部（第{i+1}次下滑），提前停止"
                            print(f"\n🎯 {early_stop_msg}")
                            self.logger.info(early_stop_msg)
                            self.logger.info(f"节省下滑次数: {scroll_times - i - 1} 次")
                            break
                    else:
                        no_change_count = 0
                        last_scroll_top = current_scroll_top

                    # 检测底部提示文字
                    if self.check_if_reached_bottom(page):
                        early_stop_msg = f"✓ 检测到底部提示（第{i+1}次下滑），提前停止"
                        print(f"\n🎯 {early_stop_msg}")
                        self.logger.info(early_stop_msg)
                        self.logger.info(f"节省下滑次数: {scroll_times - i - 1} 次")
                        break

                # 单次滚动距离：600-1000px（v1.5 是 500-800px，步长更大触底更快）
                scroll_distance = random.randint(600, 1000)

                page.run_js(f"window.scrollBy(0, {scroll_distance});")

                if (i + 1) % 10 == 0 or i == 0 or i == scroll_times - 1:
                    self.logger.info(f"✓ 第 {i+1}/{scroll_times} 次下滑完成")

                # 延迟策略（保持与 v1.5 相同，已是最优的随机区间）
                if self.fast_scroll_mode:
                    if i < scroll_times * 0.2:
                        delay = random.uniform(0.3, 0.5)
                    elif i < scroll_times * 0.8:
                        delay = random.uniform(0.4, 0.7)
                    else:
                        delay = random.uniform(0.3, 0.6)
                else:
                    if i < scroll_times * 0.3:
                        delay = random.uniform(1.0, 2.0)
                    elif i < scroll_times * 0.7:
                        delay = random.uniform(2.0, 4.0)
                    else:
                        delay = random.uniform(1.2, 2.5)

                time.sleep(delay)

                # 偶发性额外停顿（风控保护）：间隔拉长到 12-18 次（v1.5 是 10-15 次）
                if (i + 1) % random.randint(12, 18) == 0:
                    extra_delay = random.uniform(1.5, 3.0)
                    self.logger.debug(f"第 {i+1} 次下滑，额外停顿 {extra_delay:.2f} 秒...")
                    time.sleep(extra_delay)

            self.logger.info("✓ 页面下滑完成")

        except Exception as e:
            self.logger.error(f"下滑页面失败: {e}")
            self.logger.error(traceback.format_exc())
    
    def crawl_city_keyword(self, page, city_name, city_code, keyword):
        """
        抓取指定城市和关键词的职位数据（通过直接访问URL）
        
        Args:
            page: 浏览器页面对象
            city_name: 城市名称（如"北京"）
            city_code: 城市编号（如"101010100"）
            keyword: 搜索关键词
        
        Returns:
            tuple: (success, jobs, error_reason)
              - success: bool，是否成功
              - jobs: list，抓取到的职位数据
              - error_reason: str，失败原因（成功时为空）
        """
        all_jobs = []
        
        try:
            # 任务开始提示（控制台+日志）
            task_header = "=" * 70
            task_title = f"🚀 开始任务: {city_name} - {keyword}"
            print(f"\n{task_header}")
            print(task_title)
            print(task_header)
            
            self.logger.info(f"{'='*60}")
            self.logger.info(f"城市: {city_name} ({city_code}) - 关键词: {keyword}")
            self.logger.info(f"{'='*60}")
            
            # ========== 步骤1: 启动网络监听 ==========
            # ⚠️ 重要：必须在访问URL之前启动监听，否则会漏掉第一页数据
            # 监听BOSS直聘职位列表API
            target_packet_name = 'wapi/zpgeek/search/joblist'
            
            self.logger.info(f"启动网络监听，目标包: {target_packet_name}")
            
            # 监听joblist接口
            page.listen.start(target_packet_name)
            self.logger.info("✓ 监听已启动")
            
            # ========== 步骤2: 直接访问目标URL ==========
            # 构建URL：https://www.zhipin.com/web/geek/jobs?city={city_code}&query={keyword}
            # 注意：使用浏览器原生编码，不手动编码中文（更自然）
            target_url = f"https://www.zhipin.com/web/geek/jobs?city={city_code}&query={keyword}"
            
            self.logger.info(f"访问URL: {target_url}")
            page.get(target_url)
            
            # 等待页面加载
            self.logger.info("等待页面加载（监听会捕获第一页数据包）...")
            page.wait.doc_loaded(timeout=15)
            self.human_like_delay(2, 3)

            # ===== 关键：验证当前 URL，检测是否被重定向回首页 =====
            current_url = page.url or ''
            self.logger.info(f"当前页面URL: {current_url}")
            if 'geek/jobs' not in current_url and 'zpgeek' not in current_url:
                redirect_msg = f"⚠️ 被重定向！目标={target_url}，实际={current_url}"
                self.logger.warning(redirect_msg)
                return False, [], redirect_msg

            # 【新增】检测风控
            if self.enable_risk_detection:
                is_blocked, reason = self.check_risk_control(page)
                if is_blocked:
                    error_msg = f"⚠️  检测到风控: {reason}"
                    print(f"\n{error_msg}")
                    self.logger.error(error_msg)
                    return False, [], reason
            
            # 【优化】减少初始浏览延迟
            browse_delay = random.uniform(0.8, 1.5)  # 优化：1-2秒 → 0.8-1.5秒
            self.logger.info(f"模拟浏览页面 {browse_delay:.2f} 秒...")
            time.sleep(browse_delay)
            
            # 【优化】简化人类交互模拟（可选）
            if random.random() < 0.3:  # 只有30%概率执行，减少耗时
                self.simulate_human_interaction(page)
            
            # ========== 步骤3: 下滑页面触发更多数据加载 ==========
            # ⚠️ 重要：Boss直聘每个关键词约300条数据，需要下滑55次才能完全加载
            # 测试模式：只下滑5次，快速验证功能
            if self.test_mode:
                actual_scroll_times = self.test_scroll_times
                scroll_msg = f"🧪 测试模式：下滑 {actual_scroll_times} 次（正常模式55次）"
                print(scroll_msg)
                self.logger.info(scroll_msg)
            else:
                # 随机调整下滑次数，避免模式识别
                actual_scroll_times = random.randint(self.scroll_times_per_keyword - 3, self.scroll_times_per_keyword + 3)
                scroll_msg = f"⬇️  开始下滑页面触发数据加载（共{actual_scroll_times}次）..."
                print(scroll_msg)
                self.logger.info(f"开始下滑页面触发更多数据加载（共{actual_scroll_times}次）...")
            
            self.scroll_to_bottom(page, scroll_times=actual_scroll_times)
            print(f"✅ 下滑完成！")
            
            # ========== 步骤4: 获取监听到的数据包 ==========
            print(f"📦 等待并获取数据包...")
            self.logger.info("等待并获取数据包...")
            time.sleep(1.0)  # 优化：1.5秒 → 1.0秒，减少等待时间
            
            # 获取所有监听到的数据包（重要：必须在停止监听之前获取）
            try:
                print(f"🔍 正在提取数据包...")
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
                packet_msg = f"✓ 成功捕获 {len(packets)} 个数据包"
                print(f"✅ {packet_msg}")
                self.logger.info(packet_msg)
            else:
                warning_msg = f"未捕获到目标数据包: {target_packet_name}"
                print(f"⚠️  {warning_msg}")
                self.logger.warning(warning_msg)
                self.logger.info("提示：请检查网络请求是否正常，或尝试增加等待时间")
                
                # 【新增】没有数据包，可能是风控，再次检测
                if self.enable_risk_detection:
                    is_blocked, reason = self.check_risk_control(page)
                    if is_blocked:
                        error_msg = f"⚠️  检测到风控: {reason}"
                        print(f"\n{error_msg}")
                        self.logger.error(error_msg)
                        return False, [], reason
                
                # 没有数据包，返回失败
                return False, [], "未捕获到数据包"
            
            # ========== 步骤5: 提取响应数据 ==========
            if packets:
                for idx, packet in enumerate(packets, 1):
                    self.logger.debug(f"提取数据包 {idx}/{len(packets)}")
                    
                    # 提取响应数据
                    try:
                        response_body = packet.response.body
                        
                        # 如果是JSON格式，添加到列表
                        if isinstance(response_body, (dict, list)):
                            all_jobs.append(response_body)
                        else:
                            # 尝试解析JSON字符串
                            try:
                                data = json.loads(response_body)
                                all_jobs.append(data)
                            except:
                                self.logger.warning(f"数据包 {idx} 不是有效的JSON格式")
                        
                    except Exception as e:
                        self.logger.warning(f"提取数据包 {idx} 失败: {e}")
            
            # 任务完成提示（控制台+日志）
            complete_msg = f"✅ {city_name}-{keyword} 抓取完成！捕获数据包: {len(all_jobs)} 个"
            print(f"\n{complete_msg}\n")
            self.logger.info(f"✓ {city_name}-{keyword} 抓取完成")
            self.logger.info(f"  - 捕获数据包: {len(all_jobs)} 个")
            
            # 返回成功
            return True, all_jobs, ""
            
        except Exception as e:
            error_msg = f"抓取 {city_name}-{keyword} 时出错: {e}"
            print(f"\n❌ {error_msg}\n")
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            
            # 返回失败
            return False, [], str(e)
    
    def parse_job_data(self, response_data):
        """
        解析Boss直聘API返回的职位数据
        
        Args:
            response_data: API响应数据（字典或JSON字符串）
        
        Returns:
            list: 解析后的职位列表
        """
        parsed_jobs = []
        
        try:
            # 如果是字符串，先解析成字典
            if isinstance(response_data, str):
                response_data = json.loads(response_data)
            
            # 提取jobList
            job_list = response_data.get('zpData', {}).get('jobList', [])
            
            if not job_list:
                self.logger.warning("未找到jobList数据")
                return parsed_jobs
            
            # 遍历每个职位
            for job in job_list:
                try:
                    # ========== 基础信息 ==========
                    job_id = job.get('encryptJobId', '') or str(uuid.uuid4())
                    title = job.get('jobName', '').strip()
                    company = job.get('brandName', '').strip()
                    
                    # ========== 地理位置 ==========
                    city = job.get('cityName', '').strip()
                    district = job.get('areaDistrict', '').strip()
                    business_district = job.get('businessDistrict', '').strip()
                    
                    # ========== 薪资信息 ==========
                    salary_desc = job.get('salaryDesc', '').strip()
                    salary_min, salary_max = self.parse_salary(salary_desc)
                    
                    # ========== 任职要求 ==========
                    experience = job.get('jobExperience', '').strip()
                    education = job.get('jobDegree', '').strip()
                    
                    # 从jobLabels提取（备用）
                    job_labels = job.get('jobLabels', [])
                    if not experience and len(job_labels) > 0:
                        experience = job_labels[0]
                    if not education and len(job_labels) > 1:
                        education = job_labels[1]
                    
                    # ========== 技能信息 ==========
                    skills = job.get('skills', [])
                    
                    # ========== 公司信息 ==========
                    company_size = job.get('brandScaleName', '').strip()
                    company_industry = job.get('brandIndustry', '').strip()
                    company_stage = job.get('brandStageName', '').strip()
                    
                    # ========== Boss信息 ==========
                    boss_name = job.get('bossName', '').strip()
                    boss_title = job.get('bossTitle', '').strip()
                    
                    # ========== 福利信息 ==========
                    welfare_list = job.get('welfareList', [])
                    
                    # ========== 发布时间 ==========
                    publish_date = datetime.now().strftime('%Y-%m-%d')
                    
                    # ========== 构建标准化数据 ==========
                    parsed_job = {
                        # 职位基本信息
                        'job_id': job_id,
                        'title': title,
                        'company': company,
                        
                        # 地理位置
                        'city': city,
                        'district': district,
                        'business_district': business_district,
                        
                        # 薪资信息
                        'salary_min': salary_min,
                        'salary_max': salary_max,
                        'salary_text': salary_desc,
                        
                        # 任职要求
                        'experience': experience,
                        'education': education,
                        
                        # 技能列表（重要！用于技能图谱构建）
                        'skills': skills,
                        
                        # 公司信息
                        'company_size': company_size,
                        'company_industry': company_industry,
                        'company_stage': company_stage,
                        
                        # Boss信息
                        'boss_name': boss_name,
                        'boss_title': boss_title,
                        
                        # 福利信息
                        'welfare': welfare_list,
                        
                        # 发布信息
                        'publish_date': publish_date,
                        'source': 'boss直聘',
                        
                        # 原始数据（可选，便于调试）
                        '_raw': {
                            'security_id': job.get('securityId', ''),
                            'lid': job.get('lid', ''),
                            'item_id': job.get('itemId', 0)
                        }
                    }
                    
                    # 验证必需字段
                    if self.validate_job_data(parsed_job):
                        parsed_jobs.append(parsed_job)
                    else:
                        self.logger.warning(f"职位数据验证失败: {title}")
                        
                except Exception as e:
                    self.logger.warning(f"解析单个职位失败: {e}")
                    continue
            
            self.logger.info(f"✓ 成功解析 {len(parsed_jobs)}/{len(job_list)} 个职位")
            
        except Exception as e:
            self.logger.error(f"解析职位数据失败: {e}")
            self.logger.error(traceback.format_exc())
        
        return parsed_jobs
    
    def parse_salary(self, salary_text):
        """
        解析薪资文本
        
        Args:
            salary_text: 薪资描述，如 "20-30K·16薪"、"15-25K"
        
        Returns:
            tuple: (最低薪资, 最高薪资)，单位：k
        """
        if not salary_text:
            return 0, 0
        
        try:
            # 匹配模式：20-30K、20k-30k、20-30k·16薪
            import re
            pattern = r'(\d+)[kK]?-(\d+)[kK]?'
            match = re.search(pattern, salary_text)
            
            if match:
                salary_min = int(match.group(1))
                salary_max = int(match.group(2))
                return salary_min, salary_max
            else:
                # 无法解析，返回0
                return 0, 0
                
        except Exception as e:
            self.logger.warning(f"解析薪资失败: {salary_text}, 错误: {e}")
            return 0, 0
    
    def validate_job_data(self, job):
        """
        验证职位数据是否完整
        
        Args:
            job: 职位数据字典
        
        Returns:
            bool: 是否有效
        """
        # 必需字段
        required_fields = ['job_id', 'title', 'company', 'city']
        
        for field in required_fields:
            if not job.get(field):
                self.logger.debug(f"缺少必需字段: {field}")
                return False
        
        # 至少有薪资或技能信息
        if not job.get('salary_text') and not job.get('skills'):
            self.logger.debug("缺少薪资和技能信息")
            return False
        
        return True
    
    def save_city_keyword_data(self, data, city_name, keyword):
        """
        保存指定城市和关键词的数据到城市JSON文件（追加模式 + 实时去重）
        
        新方案：
          - 一个城市一个文件：data/raw/boss_北京.json
          - 追加模式：每抓完一个关键词，追加新数据到城市文件
          - 实时去重：追加前检查job_id是否已存在
          - 断点安全：中断后已保存数据不丢失
        
        Args:
            data: 数据列表（API响应数据包列表）
            city_name: 城市名称
            keyword: 关键词
        """
        if not data:
            self.logger.warning(f"{city_name}-{keyword}: 没有数据需要保存")
            return
        
        try:
            # ========== 步骤1: 解析所有数据包 ==========
            all_parsed_jobs = []
            
            print(f"\n🔄 正在解析数据: {city_name} - {keyword} (共 {len(data)} 个数据包)")
            self.logger.info(f"开始解析数据: {city_name} - {keyword}")
            
            for idx, response_data in enumerate(data, 1):
                self.logger.debug(f"解析第 {idx}/{len(data)} 个数据包")
                parsed_jobs = self.parse_job_data(response_data)
                all_parsed_jobs.extend(parsed_jobs)
                print(f"  ✓ 已解析 {idx}/{len(data)} 个数据包 (当前包: {len(parsed_jobs)} 条, 累计: {len(all_parsed_jobs)} 条)")
            
            if not all_parsed_jobs:
                warning_msg = f"{city_name}-{keyword}: 解析后没有有效数据"
                print(f"⚠️  {warning_msg}")
                self.logger.warning(warning_msg)
                return
            
            print(f"✅ 解析完成！共获得 {len(all_parsed_jobs)} 条数据\n")
            
            # ========== 测试模式：只解析不保存 ==========
            if self.test_mode:
                test_msg = f"🧪 测试模式：已解析 {len(all_parsed_jobs)} 条数据（不保存）"
                print(test_msg)
                self.logger.info(test_msg)
                # 打印统计信息
                self.print_data_statistics(all_parsed_jobs, city_name, keyword)
                return
            
            # ========== 步骤2: 加载城市文件（优先使用内存缓存，避免重复磁盘 IO）==========
            city_file = os.path.join(self.data_dir, f"boss_{city_name}.json")

            if city_name not in self.city_job_ids:
                # 第一次处理该城市：从磁盘加载，同时建立内存缓存
                if os.path.exists(city_file):
                    with open(city_file, 'r', encoding='utf-8') as f:
                        existing_jobs = json.load(f)
                    self.city_job_ids[city_name] = {job['job_id'] for job in existing_jobs if 'job_id' in job}
                    self.city_data_cache[city_name] = existing_jobs  # 缓存到内存
                    print(f"📂 加载已有数据: {len(existing_jobs)} 条 (job_id: {len(self.city_job_ids[city_name])} 个)")
                else:
                    self.city_job_ids[city_name] = set()
                    existing_jobs = []
                    self.city_data_cache[city_name] = []  # 初始化空缓存
                    print(f"📝 创建新文件: {city_file}")
            else:
                # 后续关键词：直接使用内存缓存，无需磁盘 IO
                existing_jobs = self.city_data_cache.get(city_name, [])
            
            # ========== 步骤3: 去重（基于job_id）==========
            new_jobs = []
            duplicate_count = 0
            
            for job in all_parsed_jobs:
                job_id = job.get('job_id')
                if not job_id:
                    continue
                
                # 检查是否已存在
                if job_id in self.city_job_ids[city_name]:
                    duplicate_count += 1
                else:
                    new_jobs.append(job)
                    self.city_job_ids[city_name].add(job_id)
            
            dedup_msg = f"去重处理: {len(all_parsed_jobs)} → {len(new_jobs)} 条新数据 (去除 {duplicate_count} 条重复)"
            print(f"🔧 {dedup_msg}")
            self.logger.info(dedup_msg)
            
            if not new_jobs:
                print(f"⚠️  所有数据都已存在，跳过保存")
                return
            
            # ========== 步骤4: 合并并保存到城市文件 ==========
            all_jobs = existing_jobs + new_jobs

            # 同步更新内存缓存（下次关键词直接从内存读，无需磁盘 IO）
            self.city_data_cache[city_name] = all_jobs

            print(f"💾 正在保存数据到城市文件...")

            # 不使用 indent=2：对于含数万条数据的大文件，无缩进可节省 30-50% 写入时间和磁盘空间
            with open(city_file, 'w', encoding='utf-8') as f:
                json.dump(all_jobs, f, ensure_ascii=False)

            save_msg = f"✓ 数据已保存: {city_file}"
            count_msg = f"✓ 本次新增: {len(new_jobs)} 条 | 累计: {len(all_jobs)} 条"
            print(f"✅ {save_msg}")
            print(f"✅ {count_msg}")
            self.logger.info(save_msg)
            self.logger.info(count_msg)
            
            # ========== 步骤5: 打印数据统计（只统计本次新增）==========
            self.print_data_statistics(new_jobs, city_name, keyword)
            
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            self.logger.error(traceback.format_exc())
    
    def print_data_statistics(self, jobs, city_name, keyword):
        """打印数据统计信息（同时输出到控制台和日志）"""
        if not jobs:
            return
        
        try:
            # 统计技能
            all_skills = []
            for job in jobs:
                all_skills.extend(job.get('skills', []))
            
            skill_count = len(set(all_skills))
            skill_list = sorted(set(all_skills))[:10]  # 前10个技能
            
            # 统计薪资
            salaries = [job.get('salary_max', 0) for job in jobs if job.get('salary_max', 0) > 0]
            avg_salary = sum(salaries) / len(salaries) if salaries else 0
            min_salary = min(salaries) if salaries else 0
            max_salary = max(salaries) if salaries else 0
            
            # 统计公司
            companies = set([job.get('company', '') for job in jobs if job.get('company')])
            
            # 统计学历要求
            education_stats = {}
            for job in jobs:
                edu = job.get('education', '不限')
                education_stats[edu] = education_stats.get(edu, 0) + 1
            
            # 统计经验要求
            experience_stats = {}
            for job in jobs:
                exp = job.get('experience', '不限')
                experience_stats[exp] = experience_stats.get(exp, 0) + 1
            
            # 构建统计信息
            stats_lines = [
                "",
                "=" * 70,
                f"📊 数据统计 - {city_name} - {keyword}",
                "=" * 70,
                f"✓ 职位数量: {len(jobs)} 条",
                f"✓ 公司数量: {len(companies)} 家",
                f"✓ 技能种类: {skill_count} 种",
                f"✓ 薪资范围: {min_salary}K ~ {max_salary}K (平均: {avg_salary:.1f}K)" if avg_salary > 0 else "✓ 薪资范围: 无数据",
                f"✓ 学历要求: {', '.join([f'{k}({v})' for k, v in sorted(education_stats.items(), key=lambda x: -x[1])[:3]])}",
                f"✓ 经验要求: {', '.join([f'{k}({v})' for k, v in sorted(experience_stats.items(), key=lambda x: -x[1])[:3]])}",
            ]
            
            if skill_list:
                stats_lines.append(f"✓ 热门技能: {', '.join(skill_list[:10])}" + ("..." if skill_count > 10 else ""))
            
            stats_lines.append("=" * 70)
            stats_lines.append("")
            
            # 同时输出到控制台和日志
            for line in stats_lines:
                print(line)  # 控制台输出
                self.logger.info(line)  # 日志输出
            
        except Exception as e:
            error_msg = f"统计数据失败: {e}"
            print(f"⚠️  {error_msg}")
            self.logger.warning(error_msg)
    
    def load_progress(self):
        """
        加载抓取进度（带内存缓存，避免每个任务重复读取磁盘）
        
        Returns:
            dict: 进度信息，包含已完成的城市和关键词
        """
        # 有缓存直接返回，无需磁盘 IO
        if self._progress_cache is not None:
            return self._progress_cache

        _empty = {
            'completed_cities': [],
            'current_city': None,
            'completed_keywords': [],
            'last_update': None
        }
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                self.logger.info(f"✓ 加载进度文件: {self.progress_file}")
            else:
                self.logger.info("未找到进度文件，将从头开始抓取")
                progress = _empty
        except Exception as e:
            self.logger.warning(f"加载进度文件失败: {e}")
            progress = _empty

        self._progress_cache = progress
        return self._progress_cache
    
    def save_progress(self, city_name, keyword=None, city_completed=False):
        """
        保存抓取进度（同时更新内存缓存，减少下次 load_progress 的磁盘 IO）
        
        Args:
            city_name: 当前城市名称
            keyword: 当前完成的关键词（可选）
            city_completed: 当前城市是否完成
        """
        try:
            # 直接使用/更新内存缓存，避免先读文件再写文件
            progress = self.load_progress()

            if city_completed:
                if city_name not in progress['completed_cities']:
                    progress['completed_cities'].append(city_name)
                progress['current_city'] = None
                progress['completed_keywords'] = []
            else:
                progress['current_city'] = city_name
                if keyword and keyword not in progress['completed_keywords']:
                    progress['completed_keywords'].append(keyword)

            progress['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 写入磁盘（进度文件较小，无需去掉缩进）
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

            # 缓存已在 load_progress 返回的引用上原地修改，无需重新赋值
            self.logger.debug(f"✓ 进度已保存: {city_name} - {keyword if keyword else '城市完成'}")

        except Exception as e:
            self.logger.warning(f"保存进度失败: {e}")
    
    def is_task_completed(self, city_name, keyword):
        """
        检查任务是否已完成
        
        Args:
            city_name: 城市名称
            keyword: 关键词
        
        Returns:
            bool: 是否已完成
        """
        progress = self.load_progress()
        
        # 检查城市是否已完成
        if city_name in progress['completed_cities']:
            return True
        
        # 检查关键词是否已完成
        if progress['current_city'] == city_name and keyword in progress['completed_keywords']:
            return True
        
        return False
    
    def clear_progress(self):
        """清除进度文件（重新开始），同时清空内存缓存"""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
                self.logger.info("✓ 进度文件已清除")
            self._progress_cache = None  # 清空缓存，下次从空状态重建
        except Exception as e:
            self.logger.warning(f"清除进度文件失败: {e}")
    
    def run(self, keywords=None, cities=None):
        """
        主运行函数 - 批量抓取Boss直聘职位数据（多城市多关键词）
        
        工作流程：
          1. 初始化浏览器（无痕模式 + 反检测）
          2. 访问Boss直聘并等待用户登录
          3. 双层循环处理所有城市和关键词：
             - 外层循环：遍历每个城市
             - 内层循环：遍历每个关键词
             - 直接访问URL：https://www.zhipin.com/web/geek/jobs?city={城市编号}&query={关键词}
             - 启动网络监听捕获API数据
             - 下滑页面55次触发所有数据加载
             - 提取监听到的所有数据包
             - 保存原始数据到JSON文件
          4. 关闭浏览器
        
        Args:
            keywords: 关键词列表，如果为None则使用从配置文件加载的关键词
            cities: 城市字典，如果为None则使用默认的6个城市
        
        数据保存位置：
            data/raw/boss_jobs/boss_{城市}_{关键词}_{时间戳}.json
        
        预计数据量：
            - 6个城市 × 99个关键词 × 300条/个 = 178,200条（原始）
            - 去重后约106,920条
        """
        # 如果未指定关键词，使用配置文件中的关键词
        if keywords is None:
            keywords = self.all_keywords
            
        # 如果未指定城市，使用默认城市
        if cities is None:
            cities = self.cities
            
        if not keywords:
            self.logger.error("没有可用的关键词！请先运行 scripts/generate_crawl_keywords.py")
            return
        
        if not cities:
            self.logger.error("没有可用的城市配置！")
            return
            
        page = None
        
        try:
            # 1. 初始化浏览器
            page = self.init_browser()

            # 2. 访问BOSS直聘首页
            self.logger.info("正在访问BOSS直聘...")
            page.get('https://www.zhipin.com/web/user/?ka=header-login')
            page.wait.doc_loaded(timeout=15)
            self.human_like_delay(2, 4)

            # CDP 的 addScriptToEvaluateOnNewDocument 只对【新】页面生效，
            # 当前已加载的登录页需要用 run_js 补注 webdriver 修复（只注最小代码，避免报错）
            _min_patch = """
try {
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined, configurable: true, enumerable: false});
} catch(e) {}
try { delete Navigator.prototype.webdriver; } catch(e) {}
try { delete navigator.__proto__.webdriver; } catch(e) {}
"""
            try:
                page.run_js(_min_patch)
            except Exception as _e:
                self.logger.warning(f"run_js 补注失败（不影响新页面）: {_e}")

            # 验证 navigator.webdriver 是否已隐藏，打印结果方便排查
            try:
                wd_val = page.run_js('return navigator.webdriver')
                if not wd_val:
                    self.logger.info("✓ navigator.webdriver = undefined（检测规避成功）")
                else:
                    self.logger.warning(f"⚠️ navigator.webdriver = {wd_val}（仍可能被检测！）")
            except Exception:
                pass

            # 3. 尝试复用已保存的 Cookie，否则等待扫码登录
            cookie_loaded = self._load_cookies(page)
            if cookie_loaded:
                # 刷新页面验证 Cookie 是否有效
                page.refresh()
                page.wait.doc_loaded(timeout=10)
                self.human_like_delay(2, 3)
                page_text = page.html or ''
                # 如果页面出现登录框则 Cookie 失效，仍需手动登录
                if '扫码登录' in page_text or 'login' in page.url.lower():
                    self.logger.warning("Cookie 已失效，需要重新扫码登录")
                    self.wait_for_login(page, wait_seconds=30)
                    self._save_cookies(page)
                else:
                    self.logger.info("✓ Cookie 有效，已跳过登录")
            else:
                # 全新登录，登录成功后保存 Cookie
                self.wait_for_login(page, wait_seconds=30)
                self._save_cookies(page)

            # ===== 关键：登录后先在首页正常浏览一段时间再开始抓取 =====
            # 直接从登录跳到职位搜索页，跳跃太大，BOSS风控会识别为异常行为
            self.logger.info("✓ 登录完成，先在首页浏览一段时间（模拟人类行为）...")
            try:
                page.get('https://www.zhipin.com/')
                page.wait.doc_loaded(timeout=10)
                self.human_like_delay(3, 6)   # 在首页停留 3~6 秒
                # 轻微滚动，模拟用户在看首页
                page.run_js("window.scrollBy(0, 300);")
                self.human_like_delay(1, 3)
                page.run_js("window.scrollBy(0, 200);")
                self.human_like_delay(2, 4)
            except Exception as _e:
                self.logger.warning(f"首页浏览失败（继续）: {_e}")

            # 4. 加载进度（断点续传）
            progress = None
            if self.enable_resume:
                progress = self.load_progress()
                if progress['completed_cities'] or progress['completed_keywords']:
                    self.logger.info(f"\n{'='*70}")
                    self.logger.info(f"检测到上次中断的进度：")
                    self.logger.info(f"  - 已完成城市: {', '.join(progress['completed_cities']) if progress['completed_cities'] else '无'}")
                    self.logger.info(f"  - 当前城市: {progress['current_city'] if progress['current_city'] else '无'}")
                    self.logger.info(f"  - 已完成关键词: {len(progress['completed_keywords'])}个")
                    self.logger.info(f"  - 上次更新: {progress['last_update']}")
                    self.logger.info(f"{'='*70}")
                    
                    response = input("\n是否从上次中断的地方继续？(yes/no，输入'reset'重新开始): ")
                    if response.lower() == 'reset':
                        self.clear_progress()
                        progress = self.load_progress()
                        self.logger.info("✓ 已重置进度，将从头开始抓取\n")
                    elif response.lower() not in ['yes', 'y']:
                        self.logger.info("已取消")
                        return
                    else:
                        self.logger.info("✓ 将从上次中断的地方继续\n")
            
            # 5. 双层循环：城市 × 关键词
            total_tasks = len(cities) * len(keywords)
            current_task = 0
            skipped_tasks = 0
            
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"开始抓取数据")
            self.logger.info(f"  - 城市数量: {len(cities)}")
            self.logger.info(f"  - 关键词数量: {len(keywords)}")
            self.logger.info(f"  - 总任务数: {total_tasks}")
            self.logger.info(f"{'='*70}\n")
            
            for city_idx, (city_name, city_code) in enumerate(cities.items(), 1):
                # 检查城市是否已完成
                if self.enable_resume and progress and city_name in progress['completed_cities']:
                    self.logger.info(f"⏭️  跳过已完成城市: {city_name}")
                    skipped_tasks += len(keywords)
                    continue
                
                self.logger.info(f"\n{'#'*70}")
                self.logger.info(f"# 城市 [{city_idx}/{len(cities)}]: {city_name} ({city_code})")
                self.logger.info(f"{'#'*70}\n")
                
                for keyword_idx, keyword in enumerate(keywords, 1):
                    current_task += 1
                    
                    # 检查任务是否已完成（断点续传）
                    if self.enable_resume and self.is_task_completed(city_name, keyword):
                        self.logger.info(f"⏭️  跳过已完成任务: {city_name} - {keyword}")
                        skipped_tasks += 1
                        continue
                    
                    self.logger.info(f"\n{'='*60}")
                    self.logger.info(f"任务进度: {current_task}/{total_tasks} (已跳过: {skipped_tasks})")
                    self.logger.info(f"城市: {city_name} [{city_idx}/{len(cities)}]")
                    self.logger.info(f"关键词: {keyword} [{keyword_idx}/{len(keywords)}]")
                    self.logger.info(f"{'='*60}\n")
                    
                    # 抓取数据
                    success, jobs, error_reason = self.crawl_city_keyword(page, city_name, city_code, keyword)
                    
                    # 【新增】检测连续失败
                    if not success:
                        self.consecutive_failures += 1
                        failure_msg = f"⚠️  任务失败 ({self.consecutive_failures}/{self.max_consecutive_failures}): {error_reason}"
                        print(f"\n{failure_msg}\n")
                        self.logger.warning(failure_msg)
                        
                        # 检查是否达到连续失败上限
                        if self.consecutive_failures >= self.max_consecutive_failures:
                            critical_msg = f"🛑 连续失败 {self.consecutive_failures} 次，可能触发风控，自动停止抓取！"
                            print(f"\n{'='*70}")
                            print(critical_msg)
                            print(f"{'='*70}\n")
                            self.logger.critical(critical_msg)
                            self.logger.info("进度已保存，可稍后重新运行继续抓取")
                            
                            # 保存当前进度后退出
                            if self.enable_resume:
                                self.save_progress(city_name, keyword)
                            
                            # 抛出异常，触发finally块关闭浏览器
                            raise RuntimeError(f"连续失败{self.consecutive_failures}次，自动停止")
                    else:
                        # 成功则重置连续失败计数
                        if self.consecutive_failures > 0:
                            self.logger.info(f"✓ 任务成功，重置失败计数（之前: {self.consecutive_failures}）")
                            self.consecutive_failures = 0
                    
                    # 保存数据
                    if jobs:
                        self.save_city_keyword_data(jobs, city_name, keyword)
                    
                    # 保存进度（断点续传）
                    if self.enable_resume:
                        self.save_progress(city_name, keyword)
                    
                    # 任务间延迟（避免风控）
                    if current_task < total_tasks:
                        # 增加随机性：每N个任务休息一次
                        if keyword_idx % self.long_break_interval == 0:
                            delay = random.uniform(self.long_break_min, self.long_break_max)
                            self.logger.info(f"\n⏰ 第{keyword_idx}个关键词，长休息 {delay:.2f} 秒...\n")
                        else:
                            delay = random.uniform(self.task_interval_min, self.task_interval_max)
                            self.logger.info(f"\n⏰ 等待 {delay:.2f} 秒后继续...\n")
                        time.sleep(delay)
                
                # 标记城市完成（断点续传）
                if self.enable_resume:
                    self.save_progress(city_name, city_completed=True)
                
                # 清理内存：释放该城市的 job_id 集合和数据缓存
                if city_name in self.city_job_ids:
                    del self.city_job_ids[city_name]
                if city_name in self.city_data_cache:
                    del self.city_data_cache[city_name]
                self.logger.info(f"✓ 已释放城市 {city_name} 的内存缓存（job_id 集合 + 数据缓存）")
                
                # 城市间的额外延迟
                if city_idx < len(cities):
                    extra_delay = random.uniform(10, 15)
                    self.logger.info(f"\n{'='*60}")
                    self.logger.info(f"✓ 城市 {city_name} 完成")
                    self.logger.info(f"⏰ 等待 {extra_delay:.2f} 秒后处理下一个城市...")
                    self.logger.info(f"{'='*60}\n")
                    time.sleep(extra_delay)
            
            self.logger.info("\n" + "="*70)
            self.logger.info("✓✓✓ 所有任务处理完成！✓✓✓")
            self.logger.info(f"  - 处理城市: {len(cities)}个")
            self.logger.info(f"  - 处理关键词: {len(keywords)}个")
            self.logger.info(f"  - 总任务数: {total_tasks}个")
            self.logger.info(f"  - 跳过任务: {skipped_tasks}个")
            self.logger.info(f"  - 实际执行: {total_tasks - skipped_tasks}个")
            self.logger.info("="*70)
            
            # 清除进度文件（所有任务完成）
            if self.enable_resume:
                self.clear_progress()
                self.logger.info("✓ 所有任务完成，进度文件已清除")
            
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
    """
    运行爬虫主程序 - 多城市多关键词版本
    
    使用方式：
      1. 运行此脚本会自动从 data/crawl_keywords.json 加载关键词
      2. 自动遍历6个城市（北京、上海、广州、深圳、杭州、成都）
      3. 每个城市抓取所有关键词的数据
    
    数据量说明：
      - 城市数量：6个
      - 关键词总数：99个（从技能词典自动生成）
      - 每个城市每个关键词：约300条职位（下滑55次确保完整）
      - 预计总数：6 × 99 × 300 = 178,200条原始数据
      - 去重后：约106,920条（优秀级别）
    
    执行时间：
      - 每个任务（城市+关键词）约需2-3分钟（包含下滑和等待）
      - 总任务数：6 × 99 = 594个任务
      - 预计总耗时：约20-30小时
    
    注意事项：
      1. 确保已运行 scripts/generate_crawl_keywords.py 生成关键词列表
      2. 启动后会打开浏览器，需要手动扫码登录（35秒内）
      3. 数据会实时保存到 data/raw/boss_jobs/ 目录
      4. 文件命名：boss_{城市}_{关键词}_{时间戳}.json
      5. 如遇到反爬，可暂停后重新运行（已保存的数据不会丢失）
    """
    
    # 创建爬虫实例
    spider = BossZhipinSpider()
    
    # 显示配置信息
    print("\n" + "="*70)
    print(f"Boss直聘批量爬虫 v{spider.VERSION} - 多城市多关键词版本")
    print("="*70)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"城市数量: {len(spider.cities)}")
    print(f"城市列表: {', '.join(spider.cities.keys())}")
    print(f"关键词总数: {len(spider.all_keywords)}")
    print(f"每个关键词下滑次数: {spider.scroll_times_per_keyword}")
    print(f"总任务数: {len(spider.cities)} × {len(spider.all_keywords)} = {len(spider.cities) * len(spider.all_keywords)}")
    print(f"数据保存目录: {spider.data_dir}")
    print(f"关键词配置文件: {spider.keywords_config_file}")
    print("="*70)
    
    if spider.all_keywords and spider.cities:
        print("\n关键词预览（前10个）：")
        for i, kw in enumerate(spider.all_keywords[:10], 1):
            print(f"  {i}. {kw}")
        if len(spider.all_keywords) > 10:
            print(f"  ... 还有 {len(spider.all_keywords) - 10} 个关键词")
        
        print("\n预计数据量（全部城市）：")
        total_raw = len(spider.cities) * len(spider.all_keywords) * 300
        total_dedup = int(total_raw * 0.6)
        print(f"  - 原始数据：约 {total_raw:,} 条")
        print(f"  - 去重后：约 {total_dedup:,} 条")
        
        # ========== 分批次抓取模式 ==========
        # 新城市列表，每5个一批
        new_city_items = list(spider.cities_new.items())
        batch_size = 5
        batches = [new_city_items[i:i+batch_size] for i in range(0, len(new_city_items), batch_size)]

        print("\n" + "="*70)
        print("抓取模式选择")
        print("="*70)
        print("1. 单城市模式（推荐）：从已有城市中选1个，约4-5小时")
        print("2. 全部已有城市模式：一次性抓取全部已配置城市，约20-30小时")
        print("3. 🧪 测试模式：快速测试少量数据（不保存），约2-3分钟")
        print("─"*70)
        print("── 新城市抓取 ──")
        print(f"4. 新城市批次模式（每批5个城市，共{len(batches)}批）：每批约20-25小时")
        for bi, batch in enumerate(batches, 1):
            city_names = "、".join(c[0] for c in batch)
            print(f"   第{bi}批: {city_names}")
        print(f"5. 全部新城市模式：一次性抓取全部{len(spider.cities_new)}个新城市，约{len(spider.cities_new)*4}-{len(spider.cities_new)*5}小时")
        print("="*70)

        mode = input("\n请选择模式 (1/2/3/4/5): ").strip()
        
        if mode == "1":
            # 单城市模式
            print("\n可选城市：")
            city_list = list(spider.cities.keys())
            for idx, city in enumerate(city_list, 1):
                print(f"  {idx}. {city} ({spider.cities[city]})")
            
            print(f"  {len(city_list) + 1}. 全部城市（一次性抓取）")
            
            city_choice = input(f"\n请选择要抓取的城市 (1-{len(city_list) + 1}): ").strip()
            
            try:
                choice_num = int(city_choice)
                if 1 <= choice_num <= len(city_list):
                    # 选择单个城市
                    selected_city = city_list[choice_num - 1]
                    selected_cities = {selected_city: spider.cities[selected_city]}
                    
                    # 计算单城市数据量
                    single_city_raw = len(spider.all_keywords) * 300
                    single_city_dedup = int(single_city_raw * 0.6)
                    
                    print("\n" + "="*70)
                    print(f"已选择：{selected_city}")
                    print("="*70)
                    print(f"关键词数量: {len(spider.all_keywords)}")
                    print(f"任务数: {len(spider.all_keywords)}")
                    print(f"预计数据量: {single_city_raw:,} 条（去重后 {single_city_dedup:,} 条）")
                    print(f"预计耗时: 4-5 小时")
                    print("="*70)
                    
                    confirm = input("\n确认开始抓取? (yes/no): ")
                    if confirm.lower() in ['yes', 'y']:
                        spider.run(cities=selected_cities)
                    else:
                        print("已取消")
                        
                elif choice_num == len(city_list) + 1:
                    # 选择全部城市
                    print("\n⚠️  警告：全部城市模式需要连续运行20-30小时！")
                    confirm = input("确认开始抓取所有城市? (yes/no): ")
                    if confirm.lower() in ['yes', 'y']:
                        spider.run()
                    else:
                        print("已取消")
                else:
                    print("❌ 无效的选择！")
            except ValueError:
                print("❌ 请输入有效的数字！")
                
        elif mode == "2":
            # 全部城市模式
            print("\n⚠️  警告：全部城市模式需要连续运行20-30小时！")
            print("建议使用单城市模式分批次抓取，降低风险。")
            confirm = input("\n确认开始抓取所有城市? (yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                spider.run()  # 使用配置文件中的所有关键词和城市
            else:
                print("已取消")
                
        elif mode == "3":
            # 测试模式
            print("\n" + "="*70)
            print("🧪 测试模式")
            print("="*70)
            print("功能：快速验证爬虫功能，抓取少量数据")
            print("特点：")
            print("  - 只抓取1个城市的2个关键词")
            print("  - 每个关键词只下滑5次（约30-50条数据）")
            print("  - 解析并显示数据统计")
            print("  - ⚠️  不保存数据到文件")
            print("  - 耗时：约2-3分钟")
            print("="*70)
            
            # 选择测试城市
            print("\n可选测试城市：")
            city_list = list(spider.cities.keys())
            for idx, city in enumerate(city_list, 1):
                print(f"  {idx}. {city}")
            
            city_choice = input(f"\n选择测试城市 (1-{len(city_list)}，默认1-北京): ").strip()
            4
            try:
                if not city_choice:
                    choice_num = 1
                else:
                    choice_num = int(city_choice)
                
                if 1 <= choice_num <= len(city_list):
                    selected_city = city_list[choice_num - 1]
                    test_cities = {selected_city: spider.cities[selected_city]}
                    
                    # 固定测试关键词
                    test_keywords = ['Python开发', 'Java开发']
                    
                    print("\n" + "="*70)
                    print(f"🧪 测试配置")
                    print("="*70)
                    print(f"测试城市: {selected_city}")
                    print(f"测试关键词: {', '.join(test_keywords)}")
                    print(f"下滑次数: {spider.test_scroll_times}次/关键词")
                    print(f"预计数据: 约60-100条（不保存）")
                    print(f"预计耗时: 2-3分钟")
                    print("="*70)
                    
                    confirm = input("\n开始测试? (yes/no): ")
                    if confirm.lower() in ['yes', 'y', '']:
                        # 启用测试模式
                        spider.test_mode = True
                        spider.enable_resume = False  # 测试模式禁用断点续传
                        
                        print("\n🧪 测试模式已启用")
                        print("⚠️  提醒：测试数据不会保存到文件\n")
                        
                        spider.run(keywords=test_keywords, cities=test_cities)
                        
                        print("\n" + "="*70)
                        print("🎉 测试完成！")
                        print("="*70)
                        print("提示：")
                        print("  - 如果数据正常，可以使用模式1或2进行正式抓取")
                        print("  - 正式抓取会保存数据到 data/raw/boss_jobs/")
                        print("="*70)
                    else:
                        print("已取消")
                else:
                    print("❌ 无效的选择！")
            except ValueError:
                print("❌ 请输入有效的数字！")
        elif mode == "4":
            # 新城市批次模式（每批5个城市）
            print("\n" + "="*70)
            print("🗺️  新城市批次模式")
            print("="*70)
            print(f"共 {len(batches)} 批，每批5个城市，约20-25小时/批")
            print("─"*70)
            for bi, batch in enumerate(batches, 1):
                city_names = "、".join(c[0] for c in batch)
                print(f"  第{bi}批: {city_names}")
            print("="*70)

            batch_choice = input(f"\n请选择要抓取的批次 (1-{len(batches)}): ").strip()
            try:
                batch_num = int(batch_choice)
                if 1 <= batch_num <= len(batches):
                    selected_batch = dict(batches[batch_num - 1])
                    city_names = "、".join(selected_batch.keys())
                    batch_raw = len(spider.all_keywords) * 300 * len(selected_batch)
                    batch_dedup = int(batch_raw * 0.6)

                    print("\n" + "="*70)
                    print(f"已选择第{batch_num}批：{city_names}")
                    print("="*70)
                    print(f"城市数量: {len(selected_batch)}")
                    print(f"关键词数量: {len(spider.all_keywords)}")
                    print(f"任务总数: {len(selected_batch) * len(spider.all_keywords)}")
                    print(f"预计数据量: {batch_raw:,} 条（去重后约 {batch_dedup:,} 条）")
                    print(f"预计耗时: 约20-25小时")
                    print("="*70)

                    confirm = input("\n确认开始抓取? (yes/no): ")
                    if confirm.lower() in ['yes', 'y']:
                        # 每个批次使用独立的进度文件，避免多批次并发时互相覆盖
                        spider.progress_file = os.path.join(
                            PROJECT_ROOT, "data",
                            f"crawler_progress_batch{batch_num}.json"
                        )
                        print(f"📂 使用独立进度文件: crawler_progress_batch{batch_num}.json")
                        spider.cities = selected_batch
                        spider.run(cities=selected_batch)
                    else:
                        print("已取消")
                else:
                    print(f"❌ 请输入 1 到 {len(batches)} 之间的数字！")
            except ValueError:
                print("❌ 请输入有效的数字！")

        elif mode == "5":
            # 全部新城市模式
            all_new = dict(spider.cities_new)
            total_raw = len(spider.all_keywords) * 300 * len(all_new)
            total_dedup = int(total_raw * 0.6)
            est_hours_min = len(all_new) * 4
            est_hours_max = len(all_new) * 5

            print("\n" + "="*70)
            print("🗺️  全部新城市模式")
            print("="*70)
            print(f"城市数量: {len(all_new)} 个")
            print(f"城市列表: {'、'.join(all_new.keys())}")
            print(f"关键词数量: {len(spider.all_keywords)}")
            print(f"预计数据量: {total_raw:,} 条（去重后约 {total_dedup:,} 条）")
            print(f"预计耗时: {est_hours_min}-{est_hours_max} 小时（连续运行）")
            print("─"*70)
            print("⚠️  警告：耗时极长，建议使用模式4分批次抓取，降低风险！")
            print("="*70)

            confirm = input("\n确认开始抓取全部新城市? (yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                spider.cities = all_new
                spider.run(cities=all_new)
            else:
                print("已取消")

        else:
            print("❌ 无效的模式选择！")
    else:
        if not spider.all_keywords:
            print("\n❌ 未找到关键词配置！")
            print("请先运行: python scripts/generate_crawl_keywords.py")
        if not spider.cities:
            print("\n❌ 未找到城市配置！")
    
    # 【测试选项】手动指定少量关键词和城市（测试用）
    # 取消下面的注释来使用测试模式
    """
    test_keywords = ['Python开发', 'Java开发']
    test_cities = {'北京': '101010100', '上海': '101020100'}
    spider.run(keywords=test_keywords, cities=test_cities)
    """
