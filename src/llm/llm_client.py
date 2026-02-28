"""
LLM客户端统一封装
对外暴露LLMClient，内部通过单例复用 Qwen3LocalClient，
确保整个进程中 vLLM 模型只被加载一次。
"""
import logging
from typing import List, Dict, Optional

from src.llm.qwen3_local_client import get_qwen3_client

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM统一客户端（组合模式）

    通过 get_qwen3_client() 获取全局单例，避免重复加载模型占用显存。
    提供 chat() / analyze_skill_gap() 等高层接口供 RAGService 使用。
    """

    def __init__(self):
        self._client = get_qwen3_client()

    # ---- 代理基础接口 ----

    def chat(self, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 1024) -> str:
        return self._client.chat(messages, temperature=temperature, max_tokens=max_tokens)

    def extract_skills_from_jd(self, jd_text: str, known_skills=None, temperature: float = 0.1):
        return self._client.extract_skills_from_jd(jd_text, known_skills=known_skills, temperature=temperature)

    def batch_extract_skills(self, jd_texts, known_skills=None, batch_size: int = 32,
                             temperature: float = 0.1, show_progress: bool = True):
        return self._client.batch_extract_skills(
            jd_texts, known_skills=known_skills, batch_size=batch_size,
            temperature=temperature, show_progress=show_progress
        )

    def get_model_info(self) -> Dict:
        return self._client.get_model_info()

    # ---- 高层接口 ----

    def analyze_skill_gap(
        self,
        user_skills: List[str],
        target_position: str,
        required_skills: Optional[List[str]] = None
    ) -> str:
        """
        分析用户技能与目标岗位之间的差距

        Args:
            user_skills: 用户当前掌握的技能列表
            target_position: 目标岗位名称
            required_skills: 岗位要求的技能列表（可为空，由LLM自行判断）

        Returns:
            差距分析文本
        """
        user_skills_str = "、".join(user_skills) if user_skills else "（未提供）"

        if required_skills:
            required_str = "、".join(required_skills)
            skills_hint = f"岗位要求技能（参考）：{required_str}\n"
        else:
            skills_hint = ""

        prompt = f"""请对以下情况进行技能差距分析：

用户当前技能：{user_skills_str}
目标岗位：{target_position}
{skills_hint}
请提供：
1. 用户已具备的相关技能
2. 目标岗位通常要求但用户尚缺的技能
3. 建议的学习优先级（高/中/低）
4. 简要的学习路径建议

请用简洁、结构化的方式回答。
"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, temperature=0.3, max_tokens=1024)
