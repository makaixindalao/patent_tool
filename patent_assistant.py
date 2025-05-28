"""
专利撰写助手
提供专利创意生成和完整专利文档撰写功能，支持多线程处理
"""

from gemini_client import GeminiClient
from prompt_templates import PromptTemplates
from typing import List, Dict, Any, Optional
import json
import concurrent.futures
import threading


class PatentAssistant:
    """专利撰写助手类，支持多线程处理"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp", base_url: str = None):
        """
        初始化专利助手
        
        Args:
            api_key: API 密钥
            model: 使用的模型名称
            base_url: 自定义API基础URL
        """
        self.client = GeminiClient(api_key, model, base_url)
        self.templates = PromptTemplates()
        self.patents = []  # 存储生成的专利
        self._lock = threading.Lock()  # 线程锁，保护共享资源
    
    def generate_patent_ideas(
        self, 
        count: int = 5, 
        temperature: float = 0.8,
        max_workers: int = 3
    ) -> List[Dict[str, Any]]:
        """
        批量生成专利创意（多线程）
        
        Args:
            count: 生成数量
            temperature: 创意随机性
            max_workers: 最大线程数
            
        Returns:
            专利创意列表
        """
        # 创建多个提示，每个提示生成一个创意
        prompts = [self.templates.get_patent_idea_prompt() for _ in range(count)]
        
        # 使用多线程批量生成
        results = self.client.batch_generate_json(
            prompts=prompts,
            system_prompt="你是一位资深的专利专家，专门从事服务器技术领域的创新研究。请严格按照JSON格式返回结果。",
            temperature=temperature,
            max_workers=max_workers
        )
        
        # 处理结果
        patent_ideas = []
        for i, result in enumerate(results):
            if isinstance(result, dict) and "error" not in result:
                # 添加ID和生成时间
                result["id"] = f"idea_{i+1}"
                result["generated_at"] = self._get_current_time()
                patent_ideas.append(result)
            else:
                # 处理错误情况
                error_idea = {
                    "id": f"idea_{i+1}",
                    "title": f"生成失败 #{i+1}",
                    "features": ["生成过程中出现错误"],
                    "error": str(result.get("error", "未知错误")),
                    "generated_at": self._get_current_time()
                }
                patent_ideas.append(error_idea)
        
        return patent_ideas
    
    def generate_full_patent(
        self, 
        title: str, 
        features: List[str], 
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        生成完整专利文档
        
        Args:
            title: 专利标题
            features: 专利特性列表
            temperature: 生成温度
            
        Returns:
            完整的专利文档
        """
        prompt = self.templates.get_full_patent_prompt(title, features)
        
        result = self.client.generate_content(
            prompt=prompt,
            system_prompt="你是一位资深的专利撰写专家，具有20年的专利申请经验。请按照国际专利申请标准撰写完整的专利文档。",
            temperature=temperature
        )
        
        # 构建专利文档结构
        patent_doc = {
            "id": f"patent_{len(self.patents) + 1}",
            "title": title,
            "features": features,
            "content": result,
            "generated_at": self._get_current_time(),
            "status": "draft"
        }
        
        # 线程安全地添加到专利列表
        with self._lock:
            self.patents.append(patent_doc)
        
        return patent_doc
    
    def batch_generate_patents(
        self,
        patent_ideas: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_workers: int = 2
    ) -> List[Dict[str, Any]]:
        """
        批量生成完整专利文档（多线程）
        
        Args:
            patent_ideas: 专利创意列表
            temperature: 生成温度
            max_workers: 最大线程数
            
        Returns:
            完整专利文档列表
        """
        def generate_single_patent(idea):
            """生成单个专利的内部函数"""
            if "error" in idea:
                return {
                    "id": idea["id"],
                    "title": idea["title"],
                    "features": idea.get("features", []),
                    "content": f"无法生成专利内容：{idea['error']}",
                    "generated_at": self._get_current_time(),
                    "status": "error"
                }
            
            title = idea.get("title", "未知标题")
            features = idea.get("features", [])
            
            prompt = self.templates.get_full_patent_prompt(title, features)
            
            content = self.client.generate_content(
                prompt=prompt,
                system_prompt="你是一位资深的专利撰写专家，具有20年的专利申请经验。请按照国际专利申请标准撰写完整的专利文档。",
                temperature=temperature
            )
            
            return {
                "id": idea["id"].replace("idea_", "patent_"),
                "title": title,
                "features": features,
                "content": content,
                "generated_at": self._get_current_time(),
                "status": "draft"
            }
        
        # 使用线程池并发生成专利
        patents = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idea = {
                executor.submit(generate_single_patent, idea): i 
                for i, idea in enumerate(patent_ideas)
            }
            
            # 按原始顺序收集结果
            patents = [None] * len(patent_ideas)
            for future in concurrent.futures.as_completed(future_to_idea):
                index = future_to_idea[future]
                try:
                    result = future.result()
                    patents[index] = result
                except Exception as e:
                    # 处理异常情况
                    idea = patent_ideas[index]
                    patents[index] = {
                        "id": idea["id"].replace("idea_", "patent_"),
                        "title": idea.get("title", "未知标题"),
                        "features": idea.get("features", []),
                        "content": f"生成专利时出现错误：{str(e)}",
                        "generated_at": self._get_current_time(),
                        "status": "error"
                    }
        
        # 线程安全地添加到专利列表
        with self._lock:
            self.patents.extend([p for p in patents if p is not None])
        
        return patents
    
    def optimize_patent(
        self, 
        patent_content: str, 
        optimization_focus: str = "全面优化",
        temperature: float = 0.6
    ) -> str:
        """
        优化专利内容
        
        Args:
            patent_content: 原始专利内容
            optimization_focus: 优化重点
            temperature: 生成温度
            
        Returns:
            优化后的专利内容
        """
        prompt = self.templates.get_optimization_prompt(patent_content, optimization_focus)
        
        return self.client.generate_content(
            prompt=prompt,
            system_prompt="你是一位专利优化专家，擅长提升专利文档的质量和专业性。",
            temperature=temperature
        )
    
    def get_patents(self) -> List[Dict[str, Any]]:
        """获取所有专利文档"""
        with self._lock:
            return self.patents.copy()
    
    def get_patent_by_id(self, patent_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取专利文档"""
        with self._lock:
            for patent in self.patents:
                if patent["id"] == patent_id:
                    return patent.copy()
        return None
    
    def update_patent(self, patent_id: str, updates: Dict[str, Any]) -> bool:
        """更新专利文档"""
        with self._lock:
            for i, patent in enumerate(self.patents):
                if patent["id"] == patent_id:
                    self.patents[i].update(updates)
                    self.patents[i]["updated_at"] = self._get_current_time()
                    return True
        return False
    
    def delete_patent(self, patent_id: str) -> bool:
        """删除专利文档"""
        with self._lock:
            for i, patent in enumerate(self.patents):
                if patent["id"] == patent_id:
                    del self.patents[i]
                    return True
        return False
    
    def export_patents_json(self) -> str:
        """导出专利为JSON格式"""
        with self._lock:
            return json.dumps(self.patents, ensure_ascii=False, indent=2)
    
    def export_patents_text(self) -> str:
        """导出专利为文本格式"""
        with self._lock:
            text_content = []
            for patent in self.patents:
                text_content.append(f"专利标题：{patent['title']}")
                text_content.append(f"专利ID：{patent['id']}")
                text_content.append(f"生成时间：{patent['generated_at']}")
                text_content.append(f"状态：{patent['status']}")
                text_content.append("=" * 50)
                text_content.append(patent['content'])
                text_content.append("\n" + "=" * 80 + "\n")
            
            return "\n".join(text_content)
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取专利统计信息"""
        with self._lock:
            total = len(self.patents)
            draft_count = sum(1 for p in self.patents if p.get("status") == "draft")
            error_count = sum(1 for p in self.patents if p.get("status") == "error")
            
            return {
                "total_patents": total,
                "draft_patents": draft_count,
                "error_patents": error_count,
                "success_rate": (draft_count / total * 100) if total > 0 else 0
            } 