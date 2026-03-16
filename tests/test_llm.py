"""
Tests for Stage 3 LLM Integration Module.

Tests the LLMClient, PromptTemplates, and ResponseGenerator without
requiring real API keys — all LLM calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.llm.llm_client import LLMClient, LLMResponse
from backend.llm.prompt_templates import PromptTemplates
from backend.llm.response_generator import ResponseGenerator, GeneratedResponse


# ===========================================================================
# LLMClient — Initialisation
# ===========================================================================

class TestLLMClientInit:
    def test_default_provider_is_anthropic(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        client = LLMClient()
        assert client.provider == "anthropic"

    def test_provider_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        client = LLMClient()
        assert client.provider == "openai"

    def test_provider_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        client = LLMClient(provider="gemini")
        assert client.provider == "gemini"

    def test_default_model_anthropic(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        client = LLMClient(provider="anthropic")
        assert client.model == "claude-sonnet-4-6"

    def test_default_model_openai(self):
        client = LLMClient(provider="openai")
        assert client.model == "gpt-4o-mini"

    def test_default_model_gemini(self):
        client = LLMClient(provider="gemini")
        assert "gemini" in client.model.lower()

    def test_model_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")
        client = LLMClient(provider="openai")
        assert client.model == "gpt-4o"

    def test_is_configured_false_without_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(provider="anthropic")
        assert client.is_configured() is False

    def test_is_configured_true_with_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        client = LLMClient(provider="anthropic")
        assert client.is_configured() is True

    def test_repr_contains_provider(self):
        client = LLMClient(provider="openai")
        assert "openai" in repr(client)


# ===========================================================================
# LLMClient — Error handling
# ===========================================================================

class TestLLMClientErrorHandling:
    def test_generate_returns_error_response_on_failure(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
        client = LLMClient(provider="anthropic")

        with patch.object(client, "_call_anthropic", side_effect=Exception("Connection refused")):
            response = client.generate("sys", "user")

        assert response.content == ""
        assert response.error is not None
        assert "Connection refused" in response.error

    def test_generate_sets_latency_on_error(self, monkeypatch):
        client = LLMClient(provider="anthropic")
        with patch.object(client, "_call_anthropic", side_effect=RuntimeError("fail")):
            response = client.generate("sys", "user")
        assert response.latency_ms >= 0

    def test_unknown_provider_returns_error(self):
        client = LLMClient(provider="unknown_provider")
        response = client.generate("sys", "user")
        assert response.error is not None


# ===========================================================================
# PromptTemplates
# ===========================================================================

class TestPromptTemplates:
    def test_system_prompt_email_returns_string(self):
        prompt = PromptTemplates.system_prompt(channel="email")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_whatsapp_returns_string(self):
        prompt = PromptTemplates.system_prompt(channel="whatsapp")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_web_form_returns_string(self):
        prompt = PromptTemplates.system_prompt(channel="web_form")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_contains_company_name(self):
        prompt = PromptTemplates.system_prompt(channel="email", company_name="Nexora")
        assert "Nexora" in prompt

    def test_email_prompt_contains_formal_guidance(self):
        prompt = PromptTemplates.system_prompt(channel="email")
        assert "formal" in prompt.lower() or "Dear" in prompt

    def test_whatsapp_prompt_contains_concise_guidance(self):
        prompt = PromptTemplates.system_prompt(channel="whatsapp")
        assert "concise" in prompt.lower() or "brief" in prompt.lower() or "short" in prompt.lower()

    def test_kb_response_prompt_contains_customer_name(self):
        kb_results = [{"topic": "billing", "content": "Invoice help content here."}]
        prompt = PromptTemplates.kb_response_prompt(kb_results, "Sarah Chen", "email", "billing")
        assert "Sarah Chen" in prompt

    def test_kb_response_prompt_contains_channel(self):
        prompt = PromptTemplates.kb_response_prompt([], "User", "whatsapp", "general")
        assert "whatsapp" in prompt.lower()

    def test_kb_response_prompt_contains_article_content(self):
        kb_results = [{"topic": "password_reset", "content": "Reset steps here."}]
        prompt = PromptTemplates.kb_response_prompt(kb_results, "User", "email", "account")
        assert "Reset steps here" in prompt

    def test_no_kb_response_prompt_contains_intent(self):
        prompt = PromptTemplates.no_kb_response_prompt("User", "email", "security", {})
        assert "security" in prompt.lower()

    def test_no_kb_response_prompt_with_vip_context(self):
        ctx = {"found": True, "account_tier": "enterprise", "is_vip": True, "ticket_count": 5}
        prompt = PromptTemplates.no_kb_response_prompt("Ali", "email", "general", ctx)
        assert "enterprise" in prompt.lower() or "premium" in prompt.lower()

    def test_escalation_summary_prompt_contains_reason(self):
        prompt = PromptTemplates.escalation_summary_prompt("legal_complaint", "critical", "Jane")
        assert "legal" in prompt.lower() or "legal_complaint" in prompt

    def test_ticket_context_prompt_empty(self):
        prompt = PromptTemplates.ticket_context_prompt([])
        assert "No previous" in prompt or "no" in prompt.lower()

    def test_ticket_context_prompt_with_tickets(self):
        tickets = [{"ticket_ref": "TKT-001", "subject": "Billing issue", "status": "open", "priority": "high"}]
        prompt = PromptTemplates.ticket_context_prompt(tickets)
        assert "TKT-001" in prompt


# ===========================================================================
# ResponseGenerator — KB Hit
# ===========================================================================

class TestResponseGeneratorKBHit:
    def setup_method(self):
        self.generator = ResponseGenerator()

    def test_kb_hit_returns_kb_source(self):
        kb_results = {
            "matched": True,
            "results": [{"topic": "password_reset", "content": "Reset your password via Settings.", "score": 8}],
        }
        result = self.generator.generate_response(
            customer_message="How do I reset my password?",
            customer_name="Alice",
            channel="email",
            intent="account",
            kb_results=kb_results,
        )
        assert result.source == "kb"
        assert result.kb_topic == "password_reset"

    def test_kb_hit_no_llm_call(self):
        kb_results = {
            "matched": True,
            "results": [{"topic": "billing", "content": "Billing info here.", "score": 6}],
        }
        with patch.object(self.generator, "_from_llm") as mock_llm:
            self.generator.generate_response(
                customer_message="billing?", customer_name="Bob",
                channel="whatsapp", intent="billing", kb_results=kb_results,
            )
            mock_llm.assert_not_called()

    def test_kb_hit_email_contains_formal_opener(self):
        kb_results = {
            "matched": True,
            "results": [{"topic": "billing", "content": "Your invoice is in Settings > Billing.", "score": 7}],
        }
        result = self.generator.generate_response(
            "invoice?", "Sarah Chen", "email", "billing", kb_results
        )
        assert "Dear" in result.content or "Sarah" in result.content

    def test_kb_hit_whatsapp_contains_emoji(self):
        kb_results = {
            "matched": True,
            "results": [{"topic": "password_reset", "content": "Reset steps.", "score": 9}],
        }
        result = self.generator.generate_response(
            "reset?", "James", "whatsapp", "account", kb_results
        )
        assert "👋" in result.content or "😊" in result.content


# ===========================================================================
# ResponseGenerator — LLM Path
# ===========================================================================

class TestResponseGeneratorLLMFallback:
    def test_kb_miss_attempts_llm(self):
        generator = ResponseGenerator()
        kb_results = {"matched": False, "results": []}

        mock_llm_response = GeneratedResponse(
            content="Here is an AI-generated answer.",
            source="llm",
            confidence=0.75,
            provider="anthropic",
            model="claude-sonnet-4-6",
            tokens_used=150,
        )

        with patch.object(generator, "_from_llm", return_value=mock_llm_response):
            result = generator.generate_response(
                "What is the airspeed velocity of an unladen swallow?",
                "Arthur", "email", "general", kb_results,
            )

        assert result.source == "llm"
        assert "AI-generated" in result.content

    def test_llm_failure_returns_fallback(self):
        generator = ResponseGenerator()
        kb_results = {"matched": False, "results": []}

        with patch.object(generator, "_from_llm", side_effect=RuntimeError("API timeout")):
            result = generator.generate_response(
                "Unknown query", "User", "email", "general", kb_results
            )

        assert result.source == "fallback"
        assert result.content  # not empty

    def test_fallback_email_channel(self):
        generator = ResponseGenerator()
        kb_results = {"matched": False, "results": []}

        with patch.object(generator, "_from_llm", side_effect=Exception("fail")):
            result = generator.generate_response(
                "query", "John Doe", "email", "general", kb_results
            )

        assert "John Doe" in result.content or "there" in result.content
        assert result.source == "fallback"

    def test_fallback_whatsapp_channel(self):
        generator = ResponseGenerator()
        kb_results = {"matched": False, "results": []}

        with patch.object(generator, "_from_llm", side_effect=Exception("fail")):
            result = generator.generate_response(
                "query", "Maria", "whatsapp", "general", kb_results
            )

        assert "👋" in result.content
        assert result.source == "fallback"
