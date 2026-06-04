"""CogniAgent exception hierarchy."""


class CogniAgentError(Exception):
    """Base exception for all CogniAgent errors."""


class LLMError(CogniAgentError):
    """Raised when an LLM call fails."""


class ToolExecutionError(CogniAgentError):
    """Raised when a tool execution fails."""


class ConfigurationError(CogniAgentError):
    """Raised when agent configuration is invalid."""


class MemoryError(CogniAgentError):
    """Raised when a memory operation fails."""


class EvolutionError(CogniAgentError):
    """Raised when the evolution engine encounters an error."""


class MaxIterationsError(CogniAgentError):
    """Raised when the reasoning loop exceeds max iterations."""


class ContextWindowError(CogniAgentError):
    """Raised when the conversation context exceeds the model's limit."""
