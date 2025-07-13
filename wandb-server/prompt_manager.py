#!/usr/bin/env python3
"""
Prompt Management Utility for PatientHero
Loads and manages system prompts from prompt.json
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

class PromptManager:
    """Manages system prompts and response templates for PatientHero"""
    
    def __init__(self, prompt_file_path: str = None):
        """Initialize prompt manager with prompt.json file"""
        if prompt_file_path is None:
            # Look for prompt.json in parent directory (project root)
            current_dir = Path(__file__).parent
            prompt_file_path = current_dir.parent / "prompt.json"
        
        self.prompt_file_path = Path(prompt_file_path)
        self.prompts_data = self._load_prompts()
    
    def _load_prompts(self) -> Dict:
        """Load prompts from JSON file"""
        try:
            with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in prompt file: {e}")
    
    def get_system_prompt(self, model_name: str = "deepseek_r1_medical") -> str:
        """Get system prompt for specified model"""
        system_prompts = self.prompts_data.get("system_prompts", {})
        prompt_config = system_prompts.get(model_name)
        
        if not prompt_config:
            # Fallback to general medical prompt
            prompt_config = system_prompts.get("general_medical_fallback")
            if not prompt_config:
                raise ValueError(f"No system prompt found for model: {model_name}")
        
        return prompt_config.get("prompt", "")
    
    def get_safety_guidelines(self, model_name: str = "deepseek_r1_medical") -> List[str]:
        """Get safety guidelines for specified model"""
        system_prompts = self.prompts_data.get("system_prompts", {})
        prompt_config = system_prompts.get(model_name, {})
        return prompt_config.get("safety_guidelines", [])
    
    def get_demo_response(self, response_type: str, **kwargs) -> str:
        """Get demo response template with formatting"""
        demo_responses = self.prompts_data.get("demo_responses", {})
        response_config = demo_responses.get(response_type)
        
        if not response_config:
            return f"Demo response type '{response_type}' not found."
        
        template = response_config.get("template", "")
        
        # Format template with provided kwargs
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # If formatting fails, return template as-is
            return template
    
    def get_keywords(self, keyword_type: str) -> List[str]:
        """Get keywords for specified type (medical, greeting, test, emergency)"""
        safety_keywords = self.prompts_data.get("safety_keywords", {})
        return safety_keywords.get(f"{keyword_type}_keywords", [])
    
    def get_disclaimer(self, disclaimer_type: str = "standard") -> str:
        """Get disclaimer text"""
        disclaimers = self.prompts_data.get("disclaimers", {})
        return disclaimers.get(disclaimer_type, disclaimers.get("standard", ""))
    
    def is_medical_query(self, user_message: str) -> bool:
        """Check if user message contains medical keywords"""
        medical_keywords = self.get_keywords("medical")
        user_message_lower = user_message.lower()
        return any(keyword in user_message_lower for keyword in medical_keywords)
    
    def is_greeting(self, user_message: str) -> bool:
        """Check if user message is a greeting"""
        greeting_keywords = self.get_keywords("greeting")
        user_message_lower = user_message.lower().strip()
        return any(greeting in user_message_lower for greeting in greeting_keywords)
    
    def is_test_message(self, user_message: str) -> bool:
        """Check if user message is a test"""
        test_keywords = self.get_keywords("test")
        user_message_lower = user_message.lower()
        return any(keyword in user_message_lower for keyword in test_keywords)
    
    def is_emergency(self, user_message: str) -> bool:
        """Check if user message indicates emergency"""
        emergency_keywords = self.get_keywords("emergency")
        user_message_lower = user_message.lower()
        return any(keyword in user_message_lower for keyword in emergency_keywords)
    
    def generate_response(self, user_message: str, model_name: str = "DeepSeek R1") -> str:
        """Generate appropriate response based on user message"""
        user_message_lower = user_message.lower().strip()
        
        # Check for emergency first
        if self.is_emergency(user_message):
            emergency_disclaimer = self.get_disclaimer("emergency")
            return f"🚨 **MEDICAL EMERGENCY DETECTED** 🚨\n\n{emergency_disclaimer}\n\nIf you're experiencing a medical emergency, please contact emergency services immediately."
        
        # Check for greetings
        if self.is_greeting(user_message):
            return self.get_demo_response("greeting", model_name=model_name)
        
        # Check for test messages
        if self.is_test_message(user_message):
            return self.get_demo_response("test", model_name=model_name)
        
        # Check for medical questions
        if self.is_medical_query(user_message):
            return self.get_demo_response("medical_question", 
                                        user_message=user_message, 
                                        model_name=model_name)
        
        # Default to non-medical response
        return self.get_demo_response("non_medical", user_message=user_message)
    
    def get_model_info(self, model_name: str) -> Dict:
        """Get full model configuration"""
        system_prompts = self.prompts_data.get("system_prompts", {})
        return system_prompts.get(model_name, {})
    
    def list_available_models(self) -> List[str]:
        """List all available model prompts"""
        system_prompts = self.prompts_data.get("system_prompts", {})
        return list(system_prompts.keys())
    
    def get_metadata(self) -> Dict:
        """Get prompt file metadata"""
        return self.prompts_data.get("metadata", {})

# Global instance for easy access
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """Get global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager

# Convenience functions
def get_system_prompt(model_name: str = "deepseek_r1_medical") -> str:
    """Convenience function to get system prompt"""
    return get_prompt_manager().get_system_prompt(model_name)

def generate_demo_response(user_message: str, model_name: str = "DeepSeek R1") -> str:
    """Convenience function to generate demo response"""
    return get_prompt_manager().generate_response(user_message, model_name)

def get_medical_disclaimer() -> str:
    """Convenience function to get standard medical disclaimer"""
    return get_prompt_manager().get_disclaimer("standard")

if __name__ == "__main__":
    # Example usage
    pm = PromptManager()
    
    print("Available models:")
    for model in pm.list_available_models():
        print(f"- {model}")
    
    print("\nDeepSeek R1 System Prompt:")
    print(pm.get_system_prompt("deepseek_r1_medical"))
    
    print("\nTest response:")
    print(pm.generate_response("hello", "DeepSeek R1"))
