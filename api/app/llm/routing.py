"""İsteği amaç ayarındaki sağlayıcıya yönlendirir.

Sağlayıcı seçimi yalnızca ayardadır. Adaptör ilk kullanıldığında kurulur: anahtarı olmayan
sağlayıcı, ona yönlenen bir istek gelmedikçe uygulamayı engellemez.
"""

from collections.abc import Callable

from app.llm.client import AnthropicClient, LLMClient, LLMProviderError, LLMRequest, LLMResult
from app.llm.openai_client import OpenAIClient
from app.llm.purposes import Provider


class RoutingClient:
    def __init__(self, factories: dict[Provider, Callable[[], LLMClient]]) -> None:
        self._factories = factories
        self._clients: dict[Provider, LLMClient] = {}

    def complete(self, request: LLMRequest) -> LLMResult:
        provider = request.config.provider
        client = self._clients.get(provider)
        if client is None:
            factory = self._factories.get(provider)
            if factory is None:
                raise LLMProviderError(f"sağlayıcı ayarlanmamış: {provider}")
            client = self._clients[provider] = factory()
        return client.complete(request)


def routing_client(anthropic_key: str | None, openai_key: str | None) -> RoutingClient:
    factories: dict[Provider, Callable[[], LLMClient]] = {
        "anthropic": lambda: AnthropicClient(api_key=anthropic_key),
    }
    if openai_key:
        factories["openai"] = lambda: OpenAIClient(api_key=openai_key)
    return RoutingClient(factories)
