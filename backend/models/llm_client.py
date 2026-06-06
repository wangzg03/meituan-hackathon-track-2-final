import time
import logging
import random
import re
from openai import OpenAI
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=Config.BASE_URL,
            api_key=Config.API_KEY,
        )
        self.model = Config.MODEL_NAME
        self.temperature = Config.TEMPERATURE
        self.max_tokens = Config.MAX_TOKENS
        self.max_retries = Config.MAX_RETRIES
        self.interval = Config.REQUEST_INTERVAL
        self.last_request_time = 0

    @staticmethod
    def _filter_think_content(text: str) -> str:
        pattern = r'<think>.*?</think>'
        filtered = re.sub(pattern, '', text, flags=re.DOTALL)
        return filtered

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_request_time = time.time()

    def chat(self, messages, temperature=None, **kwargs):
        # 处理 temperature 参数，避免与 **kwargs 冲突
        if 'temperature' in kwargs:
            temperature = kwargs.pop('temperature')
        effective_temp = temperature if temperature is not None else self.temperature
        effective_temp = max(0.0, min(2.0, effective_temp))

        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                extra_body = {"enable_thinking": False}
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=effective_temp,
                    max_tokens=self.max_tokens,
                    extra_body=extra_body,
                    stream=True,
                    timeout=30.0,
                    **kwargs
                )
                full_content = ""
                chunk_count = 0
                for chunk in response:
                    chunk_count += 1
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        content_piece = delta.content
                        if content_piece is None:
                            content_piece = getattr(delta, 'reasoning_content', None)
                        if content_piece is None:
                            content_piece = getattr(delta, 'text', None)
                        if content_piece:
                            full_content += content_piece
                    if chunk_count == 1 and not full_content:
                        logger.debug(f"Chunk structure: {chunk}")

                if full_content.strip():
                    logger.info(f"成功提取回复，长度 {len(full_content)}")
                    return self._filter_think_content(full_content.strip())
                else:
                    logger.warning(f"流式响应为空 (共{chunk_count}块)，使用 fallback 回复")
                    return self._non_stream_fallback(messages, effective_temp)
            except Exception as e:
                logger.error(f"API调用失败 (尝试 {attempt+1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return "嗯，我明白了。"
                if hasattr(e, 'status_code') and e.status_code == 429:
                    wait_time = random.uniform(4.0, 8.0)
                    logger.info(f"429限流，等待 {wait_time:.1f}秒")
                    time.sleep(wait_time)
                else:
                    time.sleep(2 ** attempt)
        return None

    def _non_stream_fallback(self, messages, temperature):
        try:
            extra_body = {"enable_thinking": False}
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=self.max_tokens,
                extra_body=extra_body,
                stream=False,
                timeout=30.0,
            )
            content = response.choices[0].message.content
            if content:
                return self._filter_think_content(content)
            reasoning = getattr(response.choices[0].message, 'reasoning_content', None)
            if reasoning:
                return self._filter_think_content(reasoning)
            return "系统正忙，请稍后重试。"
        except Exception as e:
            logger.error(f"非流式回退失败: {e}")
            return "嗯，请继续。"

    def chat_with_system(self, system_prompt, user_message, temperature=None):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.chat(messages, temperature=temperature)