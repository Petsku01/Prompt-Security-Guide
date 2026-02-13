# Secure Chatbot Example

This example demonstrates how to implement a security-hardened chatbot using the principles from the Prompt Security Guide.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  INPUT VALIDATOR                                             │
│  ├─ Pattern detection                                        │
│  ├─ Length validation                                        │
│  └─ Rate limiting                                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  SECURE PROMPT BUILDER                                       │
│  ├─ System/user separation                                   │
│  ├─ Instruction integrity check                              │
│  └─ Context management                                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM EXECUTION (Sandboxed)                                   │
│  ├─ Capability restrictions                                  │
│  ├─ Tool access control                                      │
│  └─ Resource limits                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT VALIDATOR                                            │
│  ├─ Sensitive content detection                              │
│  ├─ Policy compliance check                                  │
│  └─ Format validation                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SAFE RESPONSE                             │
└─────────────────────────────────────────────────────────────┘
```

## Files

- `secure_chatbot.py` - Main chatbot implementation
- `validators.py` - Input/output validation functions
- `prompt_builder.py` - Secure prompt construction
- `config.yaml` - Security configuration

## Usage

```python
from secure_chatbot import SecureChatbot

# Initialize with security configuration
chatbot = SecureChatbot(config_path="config.yaml")

# Process user message securely
response = chatbot.process_message(
    user_id="user123",
    message="Hello, how can you help me?"
)

print(response)
```

## Security Features

### Input Validation
- Injection pattern detection
- Maximum length enforcement
- Rate limiting per user
- Content policy pre-check

### Prompt Security
- System/user instruction separation
- Instruction integrity verification
- Dynamic capability scoping

### Output Security
- Sensitive information filtering
- Policy compliance validation
- Response sanitization

## Configuration

```yaml
# config.yaml
security:
  max_input_length: 2000
  rate_limit:
    requests_per_minute: 10
    burst_limit: 20
  
  injection_detection:
    enabled: true
    patterns_file: "patterns.yaml"
    semantic_threshold: 0.85
  
  output_filtering:
    enabled: true
    sensitive_patterns:
      - system_prompt
      - api_keys
      - credentials
  
  capability_restrictions:
    allowed_tools: []
    max_response_tokens: 1000
```

## Testing

```bash
# Run security tests
pytest tests/ -v

# Run specific test category
pytest tests/test_injection.py -v
```

## See Also

- [Defense Strategies](../../docs/DEFENSE_STRATEGIES.md)
- [Security Scanner](../../tools/security_scanner.py)