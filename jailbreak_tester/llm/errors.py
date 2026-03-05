class LLMError(Exception):
    """Base LLM error."""


class HTTPStatusError(LLMError):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body[:300]}")


class RetryExhaustedError(LLMError):
    pass


class ParseError(LLMError):
    pass
