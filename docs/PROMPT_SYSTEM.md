# PatientHero Prompt Management System

This document describes the prompt management system for PatientHero, which centralizes all AI model prompts and response templates.

## Overview

The prompt management system consists of:

1. **`prompt.json`** - Central configuration file with all prompts and templates
2. **`wandb-server/prompt_manager.py`** - Python utility for backend services
3. **`lib/prompt-manager.ts`** - TypeScript utility for frontend services

## Files Structure

```
PatientHero/
├── prompt.json                     # Central prompt configuration
├── wandb-server/
│   └── prompt_manager.py           # Python prompt manager
└── lib/
    └── prompt-manager.ts           # TypeScript prompt manager
```

## Configuration File: `prompt.json`

### System Prompts

The configuration includes specialized prompts for different AI models:

- **`deepseek_r1_medical`** - DeepSeek R1 model prompt
- **`med42_8b_medical`** - Med42-8B model prompt  
- **`general_medical_fallback`** - Fallback prompt for any model

Each prompt includes:
- Model name and description
- Safety guidelines
- Response format requirements
- Medical disclaimers

### Demo Response Templates

Pre-defined response templates for common scenarios:

- **`greeting`** - Welcome messages
- **`test`** - System status responses
- **`medical_question`** - Medical query responses
- **`non_medical`** - Non-medical query responses

### Safety Keywords

Keyword lists for message classification:

- **`medical_keywords`** - Identifies medical queries
- **`greeting_keywords`** - Identifies greetings
- **`test_keywords`** - Identifies test messages
- **`emergency_keywords`** - Identifies emergency situations

### Disclaimers

Standard disclaimer texts:

- **`standard`** - General medical disclaimer
- **`emergency`** - Emergency situation disclaimer
- **`diagnosis`** - Diagnosis limitation disclaimer
- **`treatment`** - Treatment limitation disclaimer

## Python Usage (`prompt_manager.py`)

### Basic Usage

```python
from prompt_manager import get_prompt_manager, generate_demo_response

# Get prompt manager instance
pm = get_prompt_manager()

# Get system prompt for a model
system_prompt = pm.get_system_prompt("deepseek_r1_medical")

# Generate demo response
response = generate_demo_response("hello", "DeepSeek R1")

# Check message type
is_medical = pm.is_medical_query("what are diabetes symptoms")
is_greeting = pm.is_greeting("hello")
is_emergency = pm.is_emergency("chest pain")
```

### Available Methods

```python
# Prompt retrieval
get_system_prompt(model_name)
get_safety_guidelines(model_name)
get_demo_response(response_type, **kwargs)
get_disclaimer(disclaimer_type)

# Message classification
is_medical_query(user_message)
is_greeting(user_message)
is_test_message(user_message)
is_emergency(user_message)

# Response generation
generate_response(user_message, model_name)

# Configuration access
get_model_info(model_name)
list_available_models()
get_metadata()
```

## TypeScript Usage (`prompt-manager.ts`)

### Basic Usage

```typescript
import PromptManager from './lib/prompt-manager';
import promptConfig from './prompt.json';

// Initialize prompt manager
const pm = new PromptManager(promptConfig);

// Get system prompt
const systemPrompt = pm.getSystemPrompt('med42_8b_medical');

// Generate response
const response = pm.generateResponse('hello', 'Med42-8B');

// Check message type
const isMedical = pm.isMedicalQuery('what are diabetes symptoms');
const isGreeting = pm.isGreeting('hello');
```

### Available Methods

```typescript
// Prompt retrieval
getSystemPrompt(modelName): string
getSafetyGuidelines(modelName): string[]
getDemoResponse(responseType, variables): string
getDisclaimer(disclaimerType): string

// Message classification
isMedicalQuery(userMessage): boolean
isGreeting(userMessage): boolean
isTestMessage(userMessage): boolean
isEmergency(userMessage): boolean

// Response generation
generateResponse(userMessage, modelName): string

// Configuration access
getModelInfo(modelName): SystemPrompt
listAvailableModels(): string[]
getMetadata(): object
```

## Integration with Services

### Backend Integration

The `wandb_deepseek_service.py` has been updated to use the prompt manager:

```python
from prompt_manager import get_prompt_manager, generate_demo_response

class DeepSeekR1Service:
    def get_medical_system_prompt(self) -> str:
        prompt_manager = get_prompt_manager()
        return prompt_manager.get_system_prompt("deepseek_r1_medical")
    
    async def _simulate_deepseek_response(self, messages):
        user_message = messages[-1]["content"] if messages else ""
        prompt_manager = get_prompt_manager()
        return prompt_manager.generate_response(user_message, "DeepSeek R1")
```

### Frontend Integration

The AI service can be updated to use the TypeScript prompt manager:

```typescript
import PromptManager from './prompt-manager';
import promptConfig from '../prompt.json';

const promptManager = new PromptManager(promptConfig);

// Use in AI service
const systemPrompt = promptManager.getSystemPrompt('med42_8b_medical');
const demoResponse = promptManager.generateResponse(userMessage, 'Med42-8B');
```

## Safety Features

### Emergency Detection

The system automatically detects emergency keywords and provides appropriate responses:

```python
if pm.is_emergency(user_message):
    return "🚨 MEDICAL EMERGENCY DETECTED 🚨\n\nCall 911 immediately!"
```

### Medical Disclaimers

All medical responses include appropriate disclaimers:

- Educational purposes only
- Not a replacement for professional medical advice
- Encouragement to consult healthcare providers

### Content Filtering

The system classifies messages to ensure appropriate responses:

- Medical queries get medical information
- Greetings get welcoming responses
- Test messages get status information
- Non-medical queries get redirection

## Customization

### Adding New Models

To add a new AI model prompt:

1. Add entry to `system_prompts` in `prompt.json`
2. Include safety guidelines and response format
3. Test with both Python and TypeScript managers

### Updating Response Templates

To modify response templates:

1. Edit templates in `demo_responses` section
2. Use `{variable_name}` for dynamic content
3. Test template formatting

### Adding Safety Keywords

To add new keyword categories:

1. Add to `safety_keywords` section
2. Update classification methods if needed
3. Test keyword detection

## Testing

### Python Testing

```bash
cd wandb-server
python3 prompt_manager.py
```

### Response Testing

```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()
print(pm.generate_response("hello", "DeepSeek R1"))
print(pm.generate_response("diabetes symptoms", "DeepSeek R1"))
print(pm.generate_response("test", "DeepSeek R1"))
```

## Best Practices

1. **Consistency**: Use the same prompt manager across all services
2. **Safety**: Always include medical disclaimers in health responses
3. **Testing**: Test all prompt changes with various input types
4. **Updates**: Keep prompts synchronized between backend and frontend
5. **Documentation**: Document any custom prompt modifications

## Future Enhancements

- **Multilingual Support**: Add prompts in multiple languages
- **A/B Testing**: Support for prompt variant testing
- **Dynamic Loading**: Runtime prompt updates without restart
- **Prompt Analytics**: Track prompt effectiveness metrics
- **Role-Based Prompts**: Different prompts for different user types
