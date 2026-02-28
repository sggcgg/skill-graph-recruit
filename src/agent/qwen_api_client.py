"""
通义千问API客户端（用于Agent对话和JD生成）

说明：
- 核心技能抽取用本地Qwen2.5-1.5B（高频，零成本）
- Agent对话用通义千问API（低频，效果好）
- 混合架构展示了架构设计能力

免费额度：200万token（约10万次对话）
申请地址：https://dashscope.aliyun.com/
"""
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class QwenAPIClient:
    """
    通义千问API客户端（用于低频高质量场景）
    
    使用场景：
    1. Agent多轮对话（需要推理能力强的模型）
    2. JD生成（需要文本生成质量）
    3. 复杂查询解析
    
    不使用场景：
    1. 技能抽取（已用本地模型，零成本）
    2. 向量检索（已用本地m3e，零成本）
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-plus"):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥（从环境变量DASHSCOPE_API_KEY读取）
            model: 模型名称
                - qwen-turbo: 快速模型，适合对话
                - qwen-plus: 高质量模型，推荐
                - qwen-max: 最强模型，成本高
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY，API功能不可用")
            logger.warning("请访问 https://dashscope.aliyun.com/ 申请免费额度")
        
        self.model = model
        logger.info(f"初始化通义千问API客户端: {model}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        多轮对话
        
        Args:
            messages: 对话历史，格式：
                [
                    {"role": "system", "content": "你是..."},
                    {"role": "user", "content": "问题"},
                    {"role": "assistant", "content": "回答"}
                ]
            temperature: 温度参数（0-1），越高越随机
            max_tokens: 最大输出长度
            
        Returns:
            模型回复
        """
        if not self.api_key:
            return "❌ 未配置API密钥，请设置DASHSCOPE_API_KEY环境变量"
        
        try:
            import dashscope
            from dashscope import Generation
            
            response = Generation.call(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                result_format='message',
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                logger.error(f"API调用失败: {response.message}")
                return f"❌ API调用失败: {response.message}"
                
        except ImportError:
            logger.error("未安装dashscope库，请运行: pip install dashscope")
            return "❌ 请安装dashscope: pip install dashscope"
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            return f"❌ API调用异常: {str(e)}"
    
    def generate_jd(
        self,
        position: str,
        skills: List[str],
        requirements: Optional[Dict] = None
    ) -> str:
        """
        生成职位描述（JD）
        
        Args:
            position: 岗位名称
            skills: 技能要求列表
            requirements: 其他要求（经验、学历等）
            
        Returns:
            生成的JD文本
        """
        skills_str = "、".join(skills)
        req_str = ""
        if requirements:
            req_str = f"""
其他要求：
- 工作经验：{requirements.get('experience', '不限')}
- 学历要求：{requirements.get('education', '不限')}
- 薪资范围：{requirements.get('salary', '面议')}
"""
        
        messages = [
            {
                "role": "system",
                "content": "你是一名资深HR，擅长撰写吸引人的职位描述。"
            },
            {
                "role": "user",
                "content": f"""请为以下岗位生成一份专业的职位描述（JD）：

岗位名称：{position}
技能要求：{skills_str}
{req_str}

要求：
1. 岗位职责（3-5条）
2. 任职要求（技能+经验+学历）
3. 加分项（可选）
4. 语言简洁专业，吸引优秀候选人
"""
            }
        ]
        
        return self.chat(messages, temperature=0.7, max_tokens=800)


def test_qwen_api():
    """测试通义千问API"""
    print("="*80)
    print("🧪 测试通义千问API客户端")
    print("="*80)
    print()
    
    client = QwenAPIClient()
    
    # 测试1: 简单对话
    print("📝 测试1: 简单对话")
    print("-"*80)
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ]
    response = client.chat(messages, temperature=0.7)
    print(f"回复: {response}")
    print()
    
    # 测试2: JD生成
    print("📝 测试2: JD生成")
    print("-"*80)
    jd = client.generate_jd(
        position="Python后端开发工程师",
        skills=["Python", "Django", "MySQL", "Redis"],
        requirements={
            "experience": "1-3年",
            "education": "本科及以上",
            "salary": "10-18K"
        }
    )
    print(f"生成的JD:\n{jd}")
    print()
    
    print("="*80)
    print("✅ 测试完成")
    print("="*80)


if __name__ == "__main__":
    test_qwen_api()
