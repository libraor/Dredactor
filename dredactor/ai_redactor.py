"""AI智能脱敏模块 - 基于上下文的敏感信息识别"""

from typing import List, Optional, Tuple

from .logger import get_logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = get_logger(__name__)


class AIRedactor:
    """AI智能脱敏器

    功能：
    - 使用大模型进行上下文感知的敏感信息识别
    - 处理非结构化文本中的敏感信息
    - 支持自定义提示词
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        api_base: Optional[str] = None,
        max_tokens: int = 4096,
    ):
        """
        初始化AI脱敏器

        Args:
            api_key: OpenAI API密钥
            model: 使用的模型
            api_base: 自定义API端点
            max_tokens: 最大token数
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI库未安装。请使用: pip install openai"
            )

        self.model = model
        self.max_tokens = max_tokens

        # 初始化OpenAI客户端
        client_kwargs = {"api_key": api_key}
        if api_base:
            client_kwargs["base_url"] = api_base

        self.client = openai.OpenAI(**client_kwargs)

        # 默认提示词模板
        self.system_prompt = """你是一个专业的文档脱敏助手。你的任务是识别文本中的敏感信息并提供脱敏建议。

请识别以下类型的敏感信息：
1. 个人姓名
2. 地址信息
3. 公司名称
4. 其他特定领域的敏感信息

对于每个识别到的敏感信息，请以JSON格式返回：
{
  "items": [
    {
      "original": "原始文本",
      "type": "信息类型",
      "suggested_replacement": "建议的替换文本"
    }
  ]
}

只返回识别到的敏感信息，不要包含非敏感内容的说明。"""

    def redact_text(
        self,
        text: str,
        custom_prompt: Optional[str] = None,
    ) -> Tuple[str, List[dict]]:
        """
        使用AI对文本进行智能脱敏

        Args:
            text: 原始文本
            custom_prompt: 自定义提示词

        Returns:
            Tuple[str, List[dict]]: (脱敏后文本, 脱敏记录列表)
        """
        if not text.strip():
            return text, []

        try:
            # 构造提示词
            prompt = custom_prompt or self.system_prompt
            user_message = f"请识别并脱敏以下文本中的敏感信息：\n\n{text}"

            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,  # 低温度以获得更一致的结果
                max_tokens=min(self.max_tokens, len(text) * 2),
            )

            # 解析响应
            ai_text = response.choices[0].message.content

            # 尝试提取结构化的脱敏信息
            redaction_records = self._extract_redaction_records(ai_text)

            # 应用脱敏
            redacted_text = self._apply_redaction(text, redaction_records)

            return redacted_text, redaction_records

        except Exception as e:
            logger.error("AI脱敏失败: %s", e)
            # 失败时返回原文
            return text, []

    def _extract_redaction_records(self, ai_response: str) -> List[dict]:
        """
        从AI响应中提取脱敏记录

        Args:
            ai_response: AI返回的文本

        Returns:
            List[dict]: 脱敏记录列表
        """
        import json
        import re

        # 尝试提取JSON代码块
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", ai_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data.get("items", [])
            except json.JSONDecodeError:
                pass

        # 尝试直接解析为JSON
        try:
            data = json.loads(ai_response.strip())
            if isinstance(data, dict):
                return data.get("items", [])
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # 无法解析，返回空列表
        return []

    def _apply_redaction(self, text: str, records: List[dict]) -> str:
        """应用脱敏记录到文本

        基于位置替换，避免 str.replace() 的全局替换导致误替换。

        Args:
            text: 原始文本
            records: 脱敏记录列表

        Returns:
            str: 脱敏后的文本
        """
        if not records:
            return text

        replacements = []
        for record in records:
            original = record.get("original", "")
            replacement = record.get("suggested_replacement", "***")
            if not original:
                continue
            idx = text.find(original)
            if idx != -1:
                replacements.append((idx, idx + len(original), replacement))

        replacements.sort(key=lambda x: x[0], reverse=True)

        result = text
        for start, end, replacement in replacements:
            result = result[:start] + replacement + result[end:]

        return result

    def redact_batch(
        self,
        texts: List[str],
        custom_prompt: Optional[str] = None,
    ) -> List[Tuple[str, List[dict]]]:
        """
        批量脱敏文本

        Args:
            texts: 文本列表
            custom_prompt: 自定义提示词

        Returns:
            List[Tuple[str, List[dict]]]: 脱敏结果列表
        """
        results = []
        for text in texts:
            result = self.redact_text(text, custom_prompt)
            results.append(result)
        return results

    def set_custom_prompt(self, prompt: str) -> None:
        """
        设置自定义提示词

        Args:
            prompt: 新的提示词
        """
        self.system_prompt = prompt

    def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            bool: 连接是否成功
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )
            return True
        except Exception:
            return False


def create_ai_redactor(
    api_key: Optional[str] = None,
    model: str = "gpt-4",
    api_base: Optional[str] = None,
) -> Optional[AIRedactor]:
    """
    便捷函数：创建AI脱敏器

    Args:
        api_key: OpenAI API密钥
        model: 使用的模型
        api_base: 自定义API端点

    Returns:
        Optional[AIRedactor]: AI脱敏器实例，失败返回None
    """
    try:
        return AIRedactor(api_key=api_key, model=model, api_base=api_base)
    except ImportError:
        logger.warning("OpenAI库未安装，AI功能不可用")
        return None
