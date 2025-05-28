"""
Gemini API 客户端封装
提供简洁的 API 调用接口，支持自定义模型厂商
"""

from openai import OpenAI
import os
import time
from typing import Optional, List, Dict, Any
import json
import concurrent.futures
import threading
from functools import partial


class GeminiClient:
    """Gemini API 客户端封装类，支持多厂商和多线程"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp", base_url: str = None):
        """
        初始化 Gemini 客户端
        
        Args:
            api_key: API 密钥
            model: 使用的模型名称
            base_url: 自定义API基础URL，如果为None则使用默认Gemini URL
        """
        self.api_key = api_key
        self.model = model
        
        # 默认使用Gemini API URL，支持自定义
        if base_url is None:
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            self.base_url = base_url
            
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def generate_content(
        self, 
        prompt: str, 
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_retries: int = 3
    ) -> str:
        """
        生成内容
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数，控制随机性
            max_tokens: 最大令牌数
            max_retries: 最大重试次数
            
        Returns:
            生成的文本内容
        """
        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
                
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }
                
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                
                response = self.client.chat.completions.create(**kwargs)
                
                if response.choices and response.choices[0].message and response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    return "模型没有返回预期的内容"
                    
            except Exception as e:
                error_msg = str(e)
                
                # 检查是否是网络或临时错误
                if attempt < max_retries - 1 and any(keyword in error_msg.lower() for keyword in 
                    ['timeout', 'connection', 'network', 'rate limit', '429', '503', '502']):
                    wait_time = (attempt + 1) * 2  # 指数退避
                    time.sleep(wait_time)
                    continue
                
                return f"API 调用错误: {error_msg}"
        
        return "API 调用错误: 达到最大重试次数"
    
    def generate_json_content(
        self, 
        prompt: str, 
        system_prompt: str = "You are a helpful assistant. Always respond with valid JSON.",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        生成 JSON 格式的内容
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            
        Returns:
            解析后的 JSON 数据
        """
        try:
            content = self.generate_content(prompt, system_prompt, temperature)
            
            # 检查是否是错误响应
            if content.startswith("API 调用错误:"):
                return {"error": content}
            
            # 尝试提取 JSON 内容
            json_content = content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                if json_end != -1:
                    json_content = content[json_start:json_end].strip()
            elif "```" in content:
                # 处理没有json标记的代码块
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                if json_end != -1:
                    json_content = content[json_start:json_end].strip()
            
            # 清理JSON内容
            json_content = json_content.strip()
            if json_content.startswith('```'):
                json_content = json_content[3:].strip()
            if json_content.endswith('```'):
                json_content = json_content[:-3].strip()
            
            return json.loads(json_content)
            
        except json.JSONDecodeError as e:
            return {"error": f"无法解析 JSON 响应: {str(e)}", "raw_content": content}
        except Exception as e:
            return {"error": f"生成 JSON 内容时出错: {str(e)}"}
    
    def _generate_single_content(self, args):
        """单个内容生成的内部方法，用于多线程"""
        prompt, system_prompt, temperature = args
        return self.generate_content(prompt, system_prompt, temperature)
    
    def batch_generate(
        self, 
        prompts: List[str], 
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_workers: int = 3
    ) -> List[str]:
        """
        批量生成内容（多线程）
        
        Args:
            prompts: 提示列表
            system_prompt: 系统提示
            temperature: 温度参数
            max_workers: 最大线程数
            
        Returns:
            生成的内容列表
        """
        results = []
        
        # 准备参数
        args_list = [(prompt, system_prompt, temperature) for prompt in prompts]
        
        # 使用线程池进行并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_prompt = {
                executor.submit(self._generate_single_content, args): i 
                for i, args in enumerate(args_list)
            }
            
            # 按原始顺序收集结果
            results = [None] * len(prompts)
            for future in concurrent.futures.as_completed(future_to_prompt):
                index = future_to_prompt[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    results[index] = f"生成失败: {str(e)}"
        
        return results
    
    def batch_generate_json(
        self,
        prompts: List[str],
        system_prompt: str = "You are a helpful assistant. Always respond with valid JSON.",
        temperature: float = 0.7,
        max_workers: int = 3
    ) -> List[Dict[str, Any]]:
        """
        批量生成JSON内容（多线程）
        
        Args:
            prompts: 提示列表
            system_prompt: 系统提示
            temperature: 温度参数
            max_workers: 最大线程数
            
        Returns:
            生成的JSON数据列表
        """
        results = []
        
        def generate_single_json(prompt):
            return self.generate_json_content(prompt, system_prompt, temperature)
        
        # 使用线程池进行并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_prompt = {
                executor.submit(generate_single_json, prompt): i 
                for i, prompt in enumerate(prompts)
            }
            
            # 按原始顺序收集结果
            results = [None] * len(prompts)
            for future in concurrent.futures.as_completed(future_to_prompt):
                index = future_to_prompt[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    results[index] = {"error": f"生成失败: {str(e)}"}
        
        return results
    
    @staticmethod
    def get_predefined_providers():
        """获取预定义的模型厂商配置"""
        return {
            "Google Gemini": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "models": [
                    "gemini-2.0-flash-exp",
                    "gemini-2.5-flash-preview-05-20", 
                    "gemini-2.5-pro-preview-05-06"
                ]
            },
            "OpenAI": {
                "base_url": "https://api.openai.com/v1/",
                "models": [
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-4-turbo",
                    "gpt-3.5-turbo"
                ]
            },
            "Anthropic Claude": {
                "base_url": "https://api.anthropic.com/v1/",
                "models": [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-5-haiku-20241022",
                    "claude-3-opus-20240229"
                ]
            },
            "DeepSeek": {
                "base_url": "https://api.deepseek.com/v1/",
                "models": [
                    "deepseek-chat",
                    "deepseek-coder"
                ]
            },
            "智谱AI": {
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "models": [
                    "glm-4-plus",
                    "glm-4-0520",
                    "glm-4"
                ]
            },
            "自定义": {
                "base_url": "",
                "models": []
            }
        } 