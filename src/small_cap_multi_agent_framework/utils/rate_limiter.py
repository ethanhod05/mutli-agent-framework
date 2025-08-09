"""
Groq Rate Limiter for Multi-Agent Framework
==========================================

Smart rate limiting wrapper to handle Groq's token limits gracefully.
"""

import time
import logging
from functools import wraps
from typing import Optional
import os
from langchain_groq import ChatGroq
from litellm import RateLimitError

logger = logging.getLogger(__name__)

class GroqRateLimiter:
    """
    Smart rate limiter for Groq API calls.
    
    Handles:
    - Token rate limits (12,000 TPM on free tier)
    - Request rate limits
    - Automatic backoff and retry
    """
    
    def __init__(self, tokens_per_minute: int = 10000, safety_buffer: float = 0.8):
        """
        Initialize rate limiter.
        
        Args:
            tokens_per_minute: Max tokens per minute (set below actual limit)
            safety_buffer: Safety margin (0.8 = use 80% of limit)
        """
        self.tokens_per_minute = int(tokens_per_minute * safety_buffer)
        self.tokens_used_this_minute = 0
        self.minute_start_time = time.time()
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    def wait_if_needed(self, estimated_tokens: int = 1000):
        """
        Wait if we're approaching rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the next request
        """
        current_time = time.time()
        
        # Reset counter if a new minute has started
        if current_time - self.minute_start_time >= 60:
            self.tokens_used_this_minute = 0
            self.minute_start_time = current_time
        
        # Check if we need to wait for token limits
        if self.tokens_used_this_minute + estimated_tokens > self.tokens_per_minute:
            wait_time = 60 - (current_time - self.minute_start_time)
            if wait_time > 0:
                logger.info(f"Rate limit approaching. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.tokens_used_this_minute = 0
                self.minute_start_time = time.time()
        
        # Ensure minimum interval between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.tokens_used_this_minute += estimated_tokens

def rate_limited_groq_call(rate_limiter: GroqRateLimiter):
    """
    Decorator to add rate limiting to LLM calls.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Estimate tokens based on input
            estimated_tokens = 1000  # Conservative estimate
            
            # Wait if needed
            rate_limiter.wait_if_needed(estimated_tokens)
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        # Extract wait time from error message if possible
                        wait_time = 15  # Default wait time
                        if "try again in" in str(e):
                            try:
                                # Parse wait time from error message
                                import re
                                match = re.search(r'try again in (\d+\.?\d*)s', str(e))
                                if match:
                                    wait_time = float(match.group(1)) + 1
                            except:
                                pass
                        
                        logger.warning(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                    else:
                        raise e
                except Exception as e:
                    logger.error(f"Unexpected error in LLM call: {e}")
                    raise e
            
            return None
        return wrapper
    return decorator

class SmartGroqLLM:
    """
    Smart Groq LLM wrapper with built-in rate limiting.
    """
    
    def __init__(self, model: str = "llama-3.3-70b-versatile", 
                 max_tokens: int = 1500, temperature: float = 0.1):
        self.rate_limiter = GroqRateLimiter()
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        self.llm = ChatGroq(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=60,
            max_retries=1,  # We handle retries in the decorator
            api_key=os.getenv("GROQ_API_KEY")
        )
    
    @property
    def chat_groq(self):
        """Return the underlying ChatGroq instance with rate limiting."""
        # Apply rate limiting to the appropriate method based on version
        if hasattr(self.llm, 'invoke'):
            # Newer versions use invoke
            original_invoke = self.llm.invoke
            self.llm.invoke = rate_limited_groq_call(self.rate_limiter)(original_invoke)
        elif hasattr(self.llm, '_call'):
            # Older versions use _call
            original_call = self.llm._call
            self.llm._call = rate_limited_groq_call(self.rate_limiter)(original_call)
        elif hasattr(self.llm, '__call__'):
            # Fallback to __call__
            original_call = self.llm.__call__
            self.llm.__call__ = rate_limited_groq_call(self.rate_limiter)(original_call)
        
        return self.llm

def create_optimized_agents():
    """
    Create agents with optimized rate limiting and token usage.
    """
    
    # Create different LLM instances for different agent types
    data_cleaner_llm = SmartGroqLLM(
        model="llama-3.1-8b-instant",  # Faster model for data cleaning
        max_tokens=800,
        temperature=0.1
    ).chat_groq
    
    analysis_llm = SmartGroqLLM(
        model="llama-3.3-70b-versatile",  # Powerful model for analysis
        max_tokens=1500,
        temperature=0.1
    ).chat_groq
    
    return {
        'data_cleaner_llm': data_cleaner_llm,
        'analysis_llm': analysis_llm
    }

# Usage example for your agents.py file:
def create_rate_limited_data_cleaner():
    """Example of creating a rate-limited agent."""
    llms = create_optimized_agents()
    
    from crewai import Agent
    
    return Agent(
        role="Senior Financial Data Quality Specialist",
        goal="Clean and validate financial data with minimal token usage",
        backstory="You are efficient and concise in your data validation.",
        verbose=True,
        allow_delegation=False,
        max_iter=2,  # Reduce iterations to save tokens
        memory=True,
        tools=[],
        llm=llms['data_cleaner_llm'],
        system_message="""You are a Senior Financial Data Quality Specialist.
        Be concise and efficient. Focus on the most critical validation tasks.
        Provide clear, actionable results without excessive detail."""
    )

# Configuration suggestions for your crew.py:
GROQ_RATE_LIMIT_CONFIG = {
    'free_tier': {
        'tokens_per_minute': 10000,  # Conservative limit (actual is 12000)
        'requests_per_minute': 30,
        'safety_buffer': 0.8
    },
    'dev_tier': {
        'tokens_per_minute': 100000,
        'requests_per_minute': 300,
        'safety_buffer': 0.9
    }
}