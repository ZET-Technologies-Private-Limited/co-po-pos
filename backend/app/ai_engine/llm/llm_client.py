from typing import Optional, List, Dict, Any
import asyncio
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import SystemMessage, HumanMessage
import json
import re
import httpx
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger


class LLMClient:
    """Multi-provider LLM integration supporting OpenAI, Gemini, Claude, and Ollama."""
    
    def __init__(self, provider: Optional[str] = None):
        self.settings = get_settings()
        self.logger = SystemLogger("llm_client")
        self.provider = (provider or self.settings.llm_provider or "ollama").lower()
        self.request_timeout_sec = float(self.settings.llm_request_timeout_sec)
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM client based on provider"""
        try:
            if self.provider == "openai":
                if not self.settings.openai_api_key:
                    self.logger.warning("OpenAI API key not configured")
                    return
                self.llm = ChatOpenAI(
                    api_key=self.settings.openai_api_key,
                    model_name=self.settings.llm_model or "gpt-4-turbo-preview",
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                )
                self.logger.info("OpenAI LLM initialized")
            
            elif self.provider == "gemini":
                if not self.settings.gemini_api_key:
                    self.logger.warning("Gemini API key not configured")
                    return
                self.llm = ChatGoogleGenerativeAI(
                    google_api_key=self.settings.gemini_api_key,
                    model=self.settings.gemini_model,
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                    max_retries=0,
                    convert_system_message_to_human=True,
                )
                self.logger.info("Gemini LLM initialized")
            
            elif self.provider == "claude":
                if not self.settings.anthropic_api_key:
                    self.logger.warning("Anthropic API key not configured")
                    return
                self.llm = ChatAnthropic(
                    api_key=self.settings.anthropic_api_key,
                    model="claude-3-opus-20240229",
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                )
                self.logger.info("Claude LLM initialized")

            elif self.provider == "ollama":
                # Ollama is invoked over HTTP in generate_completion.
                # Keep llm sentinel truthy so callers can use a unified path.
                self.llm = "ollama"
                self.logger.info(
                    f"Ollama LLM initialized (base={self.settings.ollama_base_url}, model={self.settings.ollama_model})"
                )
            else:
                self.logger.error(f"Unknown provider: {self.provider}")
                return
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.provider}: {str(e)}")

    async def _resolve_ollama_model(self, client: httpx.AsyncClient) -> Optional[str]:
        """Pick a valid Ollama model, preferring configured model when available."""
        configured = (self.settings.ollama_model or "").strip()
        try:
            tags = await client.get(f"{self.settings.ollama_base_url.rstrip('/')}/api/tags")
            tags.raise_for_status()
            models = tags.json().get("models") or []
            names = [m.get("name") for m in models if isinstance(m, dict) and m.get("name")]
            if configured and configured in names:
                return configured
            if names:
                return names[0]
            return configured or None
        except Exception as e:
            self.logger.warning(f"Failed to resolve Ollama model list: {str(e)}")
            return configured or None

    async def _generate_with_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Generate text via Ollama HTTP API."""
        try:
            endpoint = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            async with httpx.AsyncClient(timeout=self.request_timeout_sec) as client:
                model_name = await self._resolve_ollama_model(client)
                if not model_name:
                    self.logger.warning("Ollama has no available models to serve the request")
                    return None
                payload = {
                    "model": model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.settings.llm_temperature,
                        "num_predict": self.settings.llm_max_tokens,
                    },
                }
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response")
                return text.strip() if isinstance(text, str) and text.strip() else None
        except Exception as e:
            self.logger.error(f"Ollama generation failed: {str(e)}")
            return None
    
    async def _invoke_langchain(self, messages: List[Any]) -> Optional[str]:
        """Invoke langchain model with a hard timeout to avoid long provider retries."""
        if not self.llm:
            return None
        response = await asyncio.wait_for(
            asyncio.to_thread(self.llm.invoke, messages),
            timeout=self.request_timeout_sec,
        )
        content = getattr(response, "content", None)
        return content if isinstance(content, str) and content.strip() else None

    async def generate_completion(
        self, prompt: str, system_prompt: Optional[str] = None,
        temperature: Optional[float] = None, max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Generate text completion"""
        if self.provider == "ollama":
            return await self._generate_with_ollama(prompt, system_prompt)

        if not self.llm:
            self.logger.warning("Primary LLM not initialized; attempting Ollama fallback")
            return await self._generate_with_ollama(prompt, system_prompt)
        
        try:
            messages = []
            if system_prompt:
                # Gemini doesn't support SystemMessage natively — merge into HumanMessage
                # convert_system_message_to_human=True handles this, but as belt-and-suspenders
                # for other providers that may not support it, we keep SystemMessage here.
                if self.provider == "gemini":
                    messages.append(HumanMessage(content=f"{system_prompt}\n\n{prompt}"))
                else:
                    messages.append(SystemMessage(content=system_prompt))
                    messages.append(HumanMessage(content=prompt))
            else:
                messages.append(HumanMessage(content=prompt))
            
            response_text = await self._invoke_langchain(messages)
            if response_text:
                self.logger.debug(f"Generated text from {self.provider}")
                return response_text
            self.logger.warning(f"Empty response from {self.provider}; trying Ollama fallback")
            return await self._generate_with_ollama(prompt, system_prompt)
        except asyncio.TimeoutError:
            self.logger.error(f"Generation timed out on {self.provider}; trying Ollama fallback")
            return await self._generate_with_ollama(prompt, system_prompt)
        except Exception as e:
            self.logger.error(f"Generation failed: {str(e)}")
            return await self._generate_with_ollama(prompt, system_prompt)
    
    async def generate_structured(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate structured JSON response"""
        if not self.llm:
            return None
        
        try:
            enhanced_prompt = f"{prompt}\n\nReturn response as valid JSON only, no markdown."
            response_text = await self.generate_completion(
                enhanced_prompt, system_prompt
            )
            
            if not response_text:
                return None
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            return None
        except Exception as e:
            self.logger.error(f"Structured generation failed: {str(e)}")
            return None
    
    async def classify_text(
        self, text: str, categories: List[str],
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Classify text into categories"""
        if not self.llm:
            return None
        
        categories_str = ", ".join(categories)
        prompt = f"Classify into: {categories_str}\n\nText: {text}\n\nReturn only category name."
        
        result = await self.generate_completion(prompt, system_prompt)
        if result:
            result = result.strip()
            if result in categories:
                return result
        return None
    
    async def extract_entities(
        self, text: str, entity_types: List[str]
    ) -> Optional[Dict[str, List[str]]]:
        """Extract entities from text"""
        entity_types_str = ", ".join(entity_types)
        prompt = f"""Extract all {entity_types_str} from:
        
{text}

Return as JSON: {{"{entity_type}": [...]}}"""
        
        return await self.generate_structured(prompt)
    
    async def generate_with_fallback(
        self, prompt: str, fallback_response: str = None
    ) -> str:
        """Generate with fallback"""
        result = await self.generate_completion(prompt)
        return result if result else (fallback_response or "")


class MultiLLMClient:
    """Manages multiple LLM providers with routing"""
    
    def __init__(self):
        settings = get_settings()
        self.clients = {
            "openai": LLMClient("openai"),
            "gemini": LLMClient("gemini"),
            "claude": LLMClient("claude"),
            "ollama": LLMClient("ollama"),
        }
        self.logger = SystemLogger("multi_llm_client")
        self.default_provider = (settings.llm_provider or "ollama").lower()
    
    async def generate(
        self, prompt: str, provider: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Generate using specified or default provider"""
        p = provider or self.default_provider
        if p not in self.clients:
            self.logger.warning(f"Unknown provider: {p}, using default")
            p = self.default_provider
        
        return await self.clients[p].generate_completion(prompt, system_prompt)
    
    async def generate_structured(
        self, prompt: str, provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate structured JSON"""
        p = provider or self.default_provider
        return await self.clients[p].generate_structured(prompt)
    
    async def compare_providers(self, prompt: str) -> Dict[str, Optional[str]]:
        """Get responses from all providers"""
        results = {}
        for provider, client in self.clients.items():
            result = await client.generate_completion(prompt)
            results[provider] = result
        return results


llm_client = LLMClient()
multi_llm_client = MultiLLMClient()
