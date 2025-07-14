"""模型管理器"""

import os
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from utils.logger import setup_logger

# 设置模型管理器logger
model_logger = setup_logger("model_manager")

@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    display_name: str
    provider: str
    model_type: str
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    streaming: bool = True
    description: str = ""

class BaseModelProvider(ABC):
    """模型提供者基类"""
    
    @abstractmethod
    def create_model(self, config: ModelConfig) -> BaseChatModel:
        """创建模型实例"""
        pass
    
    @abstractmethod
    def is_available(self, config: ModelConfig) -> bool:
        """检查模型是否可用"""
        pass

class TongyiProvider(BaseModelProvider):
    """通义千问模型提供者"""
    
    def create_model(self, config: ModelConfig) -> BaseChatModel:
        """创建通义千问模型"""
        try:
            model_kwargs = {
                "streaming": config.streaming,
            }
            
            if config.model_name:
                model_kwargs["model"] = config.model_name
            if config.max_tokens:
                model_kwargs["max_tokens"] = config.max_tokens
            if config.temperature is not None:
                model_kwargs["temperature"] = config.temperature
            
            return ChatTongyi(**model_kwargs)
        except Exception as e:
            model_logger.error(f"创建通义千问模型失败: {e}")
            raise
    
    def is_available(self, config: ModelConfig) -> bool:
        """检查通义千问是否可用"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        return api_key is not None and api_key.strip() != ""

class OpenAIProvider(BaseModelProvider):
    """OpenAI 模型提供者"""
    
    def create_model(self, config: ModelConfig) -> BaseChatModel:
        """创建 OpenAI 模型"""
        try:
            model_kwargs = {
                "streaming": config.streaming,
                "model": config.model_name or "gpt-3.5-turbo",
            }
            
            if config.max_tokens:
                model_kwargs["max_tokens"] = config.max_tokens
            if config.temperature is not None:
                model_kwargs["temperature"] = config.temperature
            if config.base_url:
                model_kwargs["base_url"] = config.base_url
            
            api_key = os.getenv(config.api_key_env or "OPENAI_API_KEY")
            if api_key:
                model_kwargs["api_key"] = api_key
            
            return ChatOpenAI(**model_kwargs)
        except Exception as e:
            model_logger.error(f"创建 OpenAI 模型失败: {e}")
            raise
    
    def is_available(self, config: ModelConfig) -> bool:
        """检查 OpenAI 是否可用"""
        api_key = os.getenv(config.api_key_env or "OPENAI_API_KEY")
        return api_key is not None and api_key.strip() != ""

class OllamaProvider(BaseModelProvider):
    """Ollama 本地模型提供者"""
    
    def create_model(self, config: ModelConfig) -> BaseChatModel:
        """创建 Ollama 模型"""
        try:
            model_kwargs = {
                "model": config.model_name or "llama2",
            }
            
            if config.base_url:
                model_kwargs["base_url"] = config.base_url
            if config.temperature is not None:
                model_kwargs["temperature"] = config.temperature
            
            return ChatOllama(**model_kwargs)
        except Exception as e:
            model_logger.error(f"创建 Ollama 模型失败: {e}")
            raise
    
    def is_available(self, config: ModelConfig) -> bool:
        """检查 Ollama 是否可用"""
        # 简单检查，可以扩展为实际连接测试
        base_url = config.base_url or "http://localhost:11434"
        try:
            import requests
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.providers: Dict[str, BaseModelProvider] = {
            "tongyi": TongyiProvider(),
            "openai": OpenAIProvider(),
            "ollama": OllamaProvider(),
        }
        
        self.model_configs: Dict[str, ModelConfig] = {
            # 通义千问系列
            "qwen-turbo": ModelConfig(
                name="qwen-turbo",
                display_name="通义千问 Turbo",
                provider="tongyi",
                model_type="chat",
                model_name="qwen-turbo",
                api_key_env="DASHSCOPE_API_KEY",
                description="阿里云通义千问快速版本，响应速度快，适合日常对话"
            ),
            "qwen-plus": ModelConfig(
                name="qwen-plus",
                display_name="通义千问 Plus",
                provider="tongyi",
                model_type="chat",
                model_name="qwen-plus",
                api_key_env="DASHSCOPE_API_KEY",
                description="阿里云通义千问增强版本，能力更强，适合复杂任务"
            ),
            "qwen-max": ModelConfig(
                name="qwen-max",
                display_name="通义千问 Max",
                provider="tongyi",
                model_type="chat",
                model_name="qwen-max",
                api_key_env="DASHSCOPE_API_KEY",
                description="阿里云通义千问旗舰版本，最强能力，适合专业场景"
            ),
            
            # OpenAI 系列
            "gpt-3.5-turbo": ModelConfig(
                name="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                provider="openai",
                model_type="chat",
                model_name="gpt-3.5-turbo",
                api_key_env="OPENAI_API_KEY",
                description="OpenAI GPT-3.5 Turbo，性价比高，适合大多数场景"
            ),
            "gpt-4": ModelConfig(
                name="gpt-4",
                display_name="GPT-4",
                provider="openai",
                model_type="chat",
                model_name="gpt-4",
                api_key_env="OPENAI_API_KEY",
                description="OpenAI GPT-4，能力最强，适合复杂推理任务"
            ),
            "gpt-4-turbo": ModelConfig(
                name="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                model_type="chat",
                model_name="gpt-4-turbo-preview",
                api_key_env="OPENAI_API_KEY",
                description="OpenAI GPT-4 Turbo，最新版本，性能和能力平衡"
            ),
            
            # Ollama 本地模型
            "llama2": ModelConfig(
                name="llama2",
                display_name="Llama 2",
                provider="ollama",
                model_type="chat",
                model_name="llama2",
                base_url="http://localhost:11434",
                description="Meta Llama 2 本地模型，免费使用，隐私保护"
            ),
            "mistral": ModelConfig(
                name="mistral",
                display_name="Mistral",
                provider="ollama",
                model_type="chat",
                model_name="mistral",
                base_url="http://localhost:11434",
                description="Mistral 本地模型，轻量高效"
            ),
            "codellama": ModelConfig(
                name="codellama",
                display_name="Code Llama",
                provider="ollama",
                model_type="chat",
                model_name="codellama",
                base_url="http://localhost:11434",
                description="专门优化的代码生成模型"
            ),
        }
        
        self.current_model: Optional[BaseChatModel] = None
        self.current_config: Optional[ModelConfig] = None
        
        model_logger.info(f"模型管理器初始化完成，支持 {len(self.model_configs)} 个模型")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        available_models = []
        
        for config in self.model_configs.values():
            provider = self.providers.get(config.provider)
            if provider and provider.is_available(config):
                available_models.append({
                    "name": config.name,
                    "display_name": config.display_name,
                    "provider": config.provider,
                    "model_type": config.model_type,
                    "description": config.description,
                    "is_current": config.name == (self.current_config.name if self.current_config else None)
                })
        
        return available_models
    
    def load_model(self, model_name: str) -> BaseChatModel:
        """加载指定模型"""
        if model_name not in self.model_configs:
            raise ValueError(f"未知模型: {model_name}")
        
        config = self.model_configs[model_name]
        provider = self.providers.get(config.provider)
        
        if not provider:
            raise ValueError(f"未支持的模型提供者: {config.provider}")
        
        if not provider.is_available(config):
            raise ValueError(f"模型 {model_name} 不可用，请检查配置和网络连接")
        
        try:
            model_logger.info(f"正在加载模型: {config.display_name}")
            model = provider.create_model(config)
            
            self.current_model = model
            self.current_config = config
            
            model_logger.info(f"模型加载成功: {config.display_name}")
            return model
            
        except Exception as e:
            model_logger.error(f"模型加载失败 {model_name}: {e}")
            raise
    
    def get_current_model(self) -> Optional[BaseChatModel]:
        """获取当前模型"""
        return self.current_model
    
    def get_current_config(self) -> Optional[ModelConfig]:
        """获取当前模型配置"""
        return self.current_config
    
    def switch_model(self, model_name: str) -> bool:
        """切换模型"""
        try:
            self.load_model(model_name)
            model_logger.info(f"切换到模型: {model_name}")
            return True
        except Exception as e:
            model_logger.error(f"切换模型失败: {e}")
            return False
    
    def add_custom_model(self, config: ModelConfig) -> bool:
        """添加自定义模型配置"""
        try:
            self.model_configs[config.name] = config
            model_logger.info(f"添加自定义模型: {config.display_name}")
            return True
        except Exception as e:
            model_logger.error(f"添加自定义模型失败: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        if model_name not in self.model_configs:
            return None
        
        config = self.model_configs[model_name]
        provider = self.providers.get(config.provider)
        
        return {
            "name": config.name,
            "display_name": config.display_name,
            "provider": config.provider,
            "model_type": config.model_type,
            "description": config.description,
            "model_name": config.model_name,
            "is_available": provider.is_available(config) if provider else False,
            "is_current": config.name == (self.current_config.name if self.current_config else None)
        }

# 全局模型管理器实例
model_manager = ModelManager()

# 尝试加载默认模型
try:
    # 优先尝试通义千问
    if model_manager.get_available_models():
        available = model_manager.get_available_models()
        default_model = None
        
        # 优先级：qwen-turbo > gpt-3.5-turbo > 其他
        for model in available:
            if model["name"] == "qwen-turbo":
                default_model = model["name"]
                break
            elif model["name"] == "gpt-3.5-turbo" and not default_model:
                default_model = model["name"]
            elif not default_model:
                default_model = model["name"]
        
        if default_model:
            model_manager.load_model(default_model)
            model_logger.info(f"默认加载模型: {default_model}")
    else:
        model_logger.warning("没有可用的模型")
        
except Exception as e:
    model_logger.error(f"加载默认模型失败: {e}")