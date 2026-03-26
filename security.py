"""
Security Module for NL2SQL Pipeline

Provides protection against LLM prompt injection attacks including:
- Direct prompt injection detection
- Typoglycemia attack detection (scrambled words)
- Encoding attack detection (Base64, hex)
- Output validation to prevent system prompt leakage
"""

import re
import base64
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_safe: bool
    sanitized_input: str
    rejection_reason: Optional[str] = None
    detected_patterns: List[str] = None
    
    def __post_init__(self):
        if self.detected_patterns is None:
            self.detected_patterns = []


class PromptInjectionFilter:
    """
    Detects and filters prompt injection attempts.
    
    Implements multiple detection strategies:
    1. Pattern matching for known injection phrases
    2. Fuzzy matching for typoglycemia attacks
    3. Encoding detection for obfuscated attacks
    """
    
    def __init__(self):
        # Dangerous patterns that indicate injection attempts
        self.dangerous_patterns = [
            # Instruction override attempts
            r'ignore\s+(all\s+)?previous\s+instructions?',
            r'ignore\s+(all\s+)?prior\s+instructions?',
            r'ignore\s+(all\s+)?above\s+instructions?',
            r'ignore\s+(all\s+)?instructions?\s+above',
            r'ignore\s+(the\s+)?instructions?',
            r'disregard\s+(all\s+)?previous\s+instructions?',
            r'forget\s+(all\s+)?previous\s+instructions?',
            r'override\s+(all\s+)?previous\s+instructions?',
            
            # Developer/admin mode attempts
            r'you\s+are\s+now\s+(in\s+)?developer\s+mode',
            r'you\s+are\s+now\s+(in\s+)?admin\s+mode',
            r'you\s+are\s+now\s+(in\s+)?jailbreak\s+mode',
            r'enter\s+(developer|admin)\s+mode',
            r'enable\s+(developer|admin)\s+mode',
            r'activate\s+(developer|admin)\s+mode',
            r'switch\s+to\s+(developer|admin|dan)\s+mode',
            r'jailbreak\s+mode',
            r'dan\s+mode',
            r'do\s+anything\s+now',
            
            # System prompt extraction
            r'reveal\s+(your\s+)?system\s+prompt',
            r'show\s+(me\s+)?(your\s+)?system\s+prompt',
            r'what\s+(are|is|were)\s+(your\s+)?(exact\s+|initial\s+)?instructions?',
            r'what\s+(are|is)\s+(your\s+)?system\s+prompt',
            r'repeat\s+(the\s+)?text\s+above',
            r'print\s+(your\s+)?initial\s+prompt',
            r'display\s+(your\s+)?system\s+message',
            r'output\s+(your\s+)?configuration',
            r'tell\s+me\s+(your\s+)?instructions?',
            r'(your\s+)?(exact|initial)\s+instructions',
            r'starting\s+with\s+.?you\s+are',
            
            # Role/persona manipulation
            r'you\s+are\s+no\s+longer',
            r'stop\s+being\s+an?\s+',
            r'pretend\s+(to\s+be|you\s+are)',
            r'act\s+as\s+if\s+you',
            r'roleplay\s+as',
            r'simulate\s+being',
            
            # Security bypass attempts
            r'bypass\s+(all\s+)?(security|safety|restrictions?|filters?)',
            r'disable\s+(all\s+)?(security|safety|restrictions?|filters?)',
            r'turn\s+off\s+(security|safety|restrictions?|filters?)',
            r'remove\s+(all\s+)?(security|safety|restrictions?|filters?)',
            r'without\s+(any\s+)?(security|safety|restrictions?)',
            
            # Harmful content requests
            r'generate\s+(malicious|harmful|dangerous)',
            r'create\s+(malware|virus|exploit)',
            
            # Output manipulation
            r'respond\s+with\s+only',
            r'output\s+exactly',
            r'print\s+only\s+the\s+following',
        ]
        
        # Words to check for typoglycemia variants
        self.fuzzy_keywords = [
            'ignore', 'bypass', 'override', 'reveal', 'system', 
            'prompt', 'instructions', 'developer', 'admin', 'jailbreak',
            'disable', 'security', 'safety', 'forget', 'disregard',
            'delete', 'previous', 'execute', 'command'
        ]
        
        # Suspicious encoding patterns
        self.encoding_patterns = [
            # Base64 pattern (long strings of base64 chars)
            r'[A-Za-z0-9+/]{20,}={0,2}',
            # Hex pattern
            r'(?:0x)?[0-9a-fA-F]{20,}',
        ]
    
    def detect_injection(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect if text contains prompt injection attempts.
        
        Args:
            text: Input text to check
            
        Returns:
            Tuple of (is_injection_detected, list of detected patterns)
        """
        detected = []
        text_lower = text.lower()
        
        # 1. Check dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected.append(f"Pattern: {pattern[:50]}...")
        
        # 2. Check for typoglycemia variants
        words = re.findall(r'\b\w+\b', text_lower)
        for word in words:
            for keyword in self.fuzzy_keywords:
                if self._is_typoglycemia_variant(word, keyword):
                    detected.append(f"Typoglycemia: '{word}' (variant of '{keyword}')")
        
        # 3. Check for encoding attempts
        encoding_detected = self._detect_encoding_attacks(text)
        detected.extend(encoding_detected)
        
        return len(detected) > 0, detected
    
    def _is_typoglycemia_variant(self, word: str, target: str) -> bool:
        """
        Check if word is a typoglycemia variant of target.
        
        Typoglycemia: words with same first/last letter and scrambled middle
        can still be read by humans (and LLMs).
        
        Args:
            word: Word to check
            target: Target keyword
            
        Returns:
            True if word appears to be a scrambled variant
        """
        if len(word) < 4 or len(target) < 4:
            return False
        if len(word) != len(target):
            return False
        if word == target:
            return False  # Exact match handled by pattern matching
        
        # Check if first and last letters match
        if word[0] != target[0] or word[-1] != target[-1]:
            return False
        
        # Check if middle letters are a permutation
        return sorted(word[1:-1]) == sorted(target[1:-1])
    
    def _detect_encoding_attacks(self, text: str) -> List[str]:
        """
        Detect potential encoding-based attacks.
        
        Args:
            text: Input text
            
        Returns:
            List of detected encoding attacks
        """
        detected = []
        
        # Check for Base64 patterns and try to decode
        base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        for match in re.finditer(base64_pattern, text):
            encoded = match.group()
            try:
                # Try to decode and check for dangerous content
                decoded = base64.b64decode(encoded).decode('utf-8', errors='ignore').lower()
                if any(keyword in decoded for keyword in ['ignore', 'bypass', 'reveal', 'system', 'prompt']):
                    detected.append(f"Base64 encoded injection detected")
                    break
            except Exception:
                pass
        
        # Check for hex-encoded content
        hex_pattern = r'(?:0x)?([0-9a-fA-F]{20,})'
        for match in re.finditer(hex_pattern, text):
            hex_str = match.group(1)
            try:
                decoded = bytes.fromhex(hex_str).decode('utf-8', errors='ignore').lower()
                if any(keyword in decoded for keyword in ['ignore', 'bypass', 'reveal', 'system', 'prompt']):
                    detected.append(f"Hex encoded injection detected")
                    break
            except Exception:
                pass
        
        return detected
    
    def sanitize_input(self, text: str, max_length: int = 10000) -> str:
        """
        Sanitize input text.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive character repetition (e.g., "aaaaaa" -> "a")
        text = re.sub(r'(.)\1{4,}', r'\1', text)
        
        # Limit length
        text = text[:max_length]
        
        return text.strip()


class OutputValidator:
    """
    Validates LLM outputs to detect potential data leakage.
    
    Checks for:
    - System prompt leakage
    - Configuration/API key exposure
    - Numbered instruction patterns
    """
    
    def __init__(self):
        self.suspicious_patterns = [
            # System prompt leakage
            r'SYSTEM\s*[:]\s*You\s+are',
            r'my\s+instructions?\s+(are|were|say)',
            r'my\s+system\s+prompt\s+(is|says|reads)',
            r'i\s+was\s+instructed\s+to',
            r'my\s+initial\s+prompt',
            
            # Configuration leakage
            r'API[_\s]?KEY\s*[:=]\s*\w+',
            r'SECRET[_\s]?KEY\s*[:=]\s*\w+',
            r'TOKEN\s*[:=]\s*\w+',
            r'PASSWORD\s*[:=]\s*\w+',
            
            # Numbered instructions (potential prompt dump)
            r'(?:instruction|rule)\s*\d+\s*:',
        ]
    
    def validate_output(self, output: str) -> Tuple[bool, List[str]]:
        """
        Validate LLM output for suspicious content.
        
        Args:
            output: LLM response to validate
            
        Returns:
            Tuple of (is_valid, list of detected issues)
        """
        issues = []
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Suspicious pattern detected: {pattern[:30]}...")
        
        return len(issues) == 0, issues
    
    def filter_response(self, response: str, max_length: int = 5000) -> str:
        """
        Filter and limit response.
        
        Args:
            response: LLM response
            max_length: Maximum allowed length
            
        Returns:
            Filtered response or error message
        """
        is_valid, issues = self.validate_output(response)
        
        if not is_valid:
            return "I cannot provide that response for security reasons."
        
        if len(response) > max_length:
            response = response[:max_length] + "... [truncated]"
        
        return response


class SecureLLMPipeline:
    """
    Orchestrates security checks for the NL2SQL pipeline.
    
    Provides:
    - Input validation and sanitization
    - Output validation
    - Security event logging (optional)
    """
    
    def __init__(self, enable_logging: bool = False):
        self.input_filter = PromptInjectionFilter()
        self.output_validator = OutputValidator()
        self.enable_logging = enable_logging
        self._security_events = []
    
    def validate_input(self, question: str, schema: str = "") -> ValidationResult:
        """
        Validate user inputs for security threats.
        
        Args:
            question: User's natural language question
            schema: Database schema input
            
        Returns:
            ValidationResult with safety status and sanitized input
        """
        # Check question for injection
        is_injection, detected = self.input_filter.detect_injection(question)
        
        if is_injection:
            if self.enable_logging:
                self._log_security_event("BLOCKED", question, detected)
            
            return ValidationResult(
                is_safe=False,
                sanitized_input=question,
                rejection_reason="Your question contains patterns that may be attempting to manipulate the system. Please rephrase your database query.",
                detected_patterns=detected
            )
        
        # Check schema for injection (less common but possible)
        is_schema_injection, schema_detected = self.input_filter.detect_injection(schema)
        
        if is_schema_injection:
            if self.enable_logging:
                self._log_security_event("BLOCKED_SCHEMA", schema, schema_detected)
            
            return ValidationResult(
                is_safe=False,
                sanitized_input=question,
                rejection_reason="The provided schema contains suspicious content. Please provide a valid database schema.",
                detected_patterns=schema_detected
            )
        
        # Sanitize inputs
        sanitized_question = self.input_filter.sanitize_input(question)
        
        return ValidationResult(
            is_safe=True,
            sanitized_input=sanitized_question
        )
    
    def validate_output(self, response: str) -> str:
        """
        Validate and filter LLM output.
        
        Args:
            response: LLM response to validate
            
        Returns:
            Validated/filtered response
        """
        return self.output_validator.filter_response(response)
    
    def _log_security_event(self, event_type: str, content: str, details: List[str]):
        """Log security event for monitoring."""
        import datetime
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": event_type,
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "details": details
        }
        self._security_events.append(event)
        
        # In production, you would send this to a logging service
        print(f"[SECURITY] {event_type}: {details}")
    
    def get_security_events(self) -> List[dict]:
        """Get recorded security events."""
        return self._security_events.copy()


# Convenience function for quick validation
def is_safe_input(text: str) -> bool:
    """
    Quick check if input is safe.
    
    Args:
        text: Input text to check
        
    Returns:
        True if input appears safe
    """
    filter = PromptInjectionFilter()
    is_injection, _ = filter.detect_injection(text)
    return not is_injection


# SQL Safety Disclaimer
SQL_SAFETY_DISCLAIMER = """
**Security Notice**: The generated SQL query is provided for reference only. 
Before executing any SQL query on your database:
1. Review the query carefully for correctness
2. Ensure it matches your intended operation
3. Test on a non-production database first
4. Never execute queries from untrusted sources without review

This tool generates SELECT queries only and does not execute any SQL.
"""
