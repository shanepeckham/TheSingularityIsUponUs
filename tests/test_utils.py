"""
Unit tests for utils.py module.
"""

import pytest
import asyncio
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    retry_with_backoff,
    RateLimiter,
    validate_positive_int,
    validate_non_negative_number,
    truncate_string,
)


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""
    
    def test_successful_function_no_retry(self):
        """Test that successful function doesn't retry."""
        call_count = []
        
        @retry_with_backoff(max_retries=3)
        def successful_func():
            call_count.append(1)
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert len(call_count) == 1
    
    def test_failing_function_retries(self):
        """Test that failing function retries correctly."""
        call_count = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def failing_func():
            call_count.append(1)
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        assert len(call_count) == 4  # Initial + 3 retries
    
    def test_eventually_successful_function(self):
        """Test function that succeeds after retries."""
        call_count = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def eventually_successful():
            call_count.append(1)
            if len(call_count) < 3:
                raise ValueError("Not yet")
            return "success"
        
        result = eventually_successful()
        assert result == "success"
        assert len(call_count) == 3
    
    @pytest.mark.asyncio
    async def test_async_function_retry(self):
        """Test retry with async functions."""
        call_count = []
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        async def async_func():
            call_count.append(1)
            if len(call_count) < 2:
                raise ValueError("Not yet")
            return "success"
        
        result = await async_func()
        assert result == "success"
        assert len(call_count) == 2
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases delays."""
        call_times = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1, exponential_base=2.0)
        def timed_func():
            call_times.append(time.time())
            raise ValueError("Test")
        
        with pytest.raises(ValueError):
            timed_func()
        
        # Check that delays increase exponentially
        assert len(call_times) == 4
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times) - 1)]
        # First delay ~0.1s, second ~0.2s, third ~0.4s
        assert delays[0] < delays[1] < delays[2]
    
    def test_max_delay_cap(self):
        """Test that delay doesn't exceed max_delay."""
        call_times = []
        
        @retry_with_backoff(
            max_retries=5,
            initial_delay=0.1,
            max_delay=0.2,
            exponential_base=2.0
        )
        def capped_func():
            call_times.append(time.time())
            raise ValueError("Test")
        
        with pytest.raises(ValueError):
            capped_func()
        
        delays = [call_times[i+1] - call_times[i] for i in range(len(call_times) - 1)]
        # All delays should be <= max_delay (0.2s) + small margin
        assert all(d <= 0.3 for d in delays)
    
    def test_specific_exception_types(self):
        """Test retry only on specific exception types."""
        call_count = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01, exceptions=(ValueError,))
        def specific_exception_func():
            call_count.append(1)
            if len(call_count) == 1:
                raise TypeError("Should not retry")
            raise ValueError("Should retry")
        
        # Should raise TypeError immediately without retry
        with pytest.raises(TypeError):
            specific_exception_func()
        
        assert len(call_count) == 1


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_rate_limiter_basic(self):
        """Test basic rate limiting functionality."""
        limiter = RateLimiter(calls_per_second=10)
        
        start = time.time()
        for _ in range(5):
            limiter.wait()
        elapsed = time.time() - start
        
        # Should take at least 0.4 seconds (5 calls at 10 calls/sec)
        assert elapsed >= 0.4
    
    def test_rate_limiter_slow_rate(self):
        """Test rate limiting with slow rate."""
        limiter = RateLimiter(calls_per_second=2)
        
        start = time.time()
        limiter.wait()
        limiter.wait()
        limiter.wait()
        elapsed = time.time() - start
        
        # Should take at least 1 second (3 calls at 2 calls/sec)
        assert elapsed >= 1.0
    
    def test_rate_limiter_invalid_rate(self):
        """Test rate limiter with invalid rate."""
        with pytest.raises(ValueError, match="must be positive"):
            RateLimiter(calls_per_second=0)
        
        with pytest.raises(ValueError, match="must be positive"):
            RateLimiter(calls_per_second=-1)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_async(self):
        """Test async rate limiting."""
        limiter = RateLimiter(calls_per_second=10)
        
        start = time.time()
        for _ in range(5):
            await limiter.wait_async()
        elapsed = time.time() - start
        
        # Should take at least 0.4 seconds
        assert elapsed >= 0.4


class TestValidationFunctions:
    """Tests for validation utility functions."""
    
    def test_validate_positive_int_valid(self):
        """Test validation of valid positive integers."""
        assert validate_positive_int(1, "test") == 1
        assert validate_positive_int(100, "test") == 100
        assert validate_positive_int(999999, "test") == 999999
    
    def test_validate_positive_int_invalid(self):
        """Test validation of invalid positive integers."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(0, "test")
        
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(-1, "test")
        
        with pytest.raises(ValueError, match="must be an integer"):
            validate_positive_int(1.5, "test")
        
        with pytest.raises(ValueError, match="must be an integer"):
            validate_positive_int("1", "test")
    
    def test_validate_non_negative_number_valid(self):
        """Test validation of valid non-negative numbers."""
        assert validate_non_negative_number(0, "test") == 0
        assert validate_non_negative_number(1, "test") == 1
        assert validate_non_negative_number(1.5, "test") == 1.5
        assert validate_non_negative_number(100.5, "test") == 100.5
    
    def test_validate_non_negative_number_invalid(self):
        """Test validation of invalid non-negative numbers."""
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_non_negative_number(-1, "test")
        
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_non_negative_number(-0.1, "test")
        
        with pytest.raises(ValueError, match="must be a number"):
            validate_non_negative_number("1", "test")


class TestTruncateString:
    """Tests for truncate_string function."""
    
    def test_truncate_short_string(self):
        """Test that short strings are not truncated."""
        text = "Short text"
        result = truncate_string(text, max_length=50)
        assert result == text
    
    def test_truncate_long_string(self):
        """Test that long strings are truncated."""
        text = "A" * 200
        result = truncate_string(text, max_length=50)
        assert len(result) == 50
        assert result.endswith("...")
    
    def test_truncate_exact_length(self):
        """Test string at exact max length."""
        text = "A" * 50
        result = truncate_string(text, max_length=50)
        assert result == text
    
    def test_truncate_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "A" * 100
        result = truncate_string(text, max_length=50, suffix="[...]")
        assert len(result) == 50
        assert result.endswith("[...]")
    
    def test_truncate_empty_string(self):
        """Test truncation of empty string."""
        result = truncate_string("", max_length=50)
        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
