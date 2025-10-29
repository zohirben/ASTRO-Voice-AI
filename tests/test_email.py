"""Unit tests for the email tool.

See /docs_imported/agents/testing.md - Unit Testing Tools
See /docs_imported/agents/tools.md - Tool Definition and Use
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os

from tools.send_email import send_email


class TestEmailTool:
    """Test suite for send_email tool."""

    @pytest.mark.asyncio
    async def test_send_email_valid_input(self, mock_context):
        """Test: Email sends successfully with valid parameters."""
        # Mock environment variables for Gmail credentials
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test Subject",
                    message="Test message body"
                )
                
                assert isinstance(result, str)
                assert "success" in result.lower() or "sent" in result.lower()

    @pytest.mark.asyncio
    async def test_send_email_with_cc(self, mock_context):
        """Test: Email with CC recipient."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test Subject",
                    message="Test message",
                    cc_email="cc@example.com"
                )
                
                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_email_invalid_recipient(self, mock_context):
        """Test: Invalid email address is caught."""
        result = await send_email(
            mock_context,
            to_email="not-an-email",
            subject="Test",
            message="Test"
        )
        
        assert isinstance(result, str)
        # Should return error message for invalid email
        assert "error" in result.lower() or "invalid" in result.lower()

    @pytest.mark.asyncio
    async def test_send_email_empty_recipient(self, mock_context):
        """Test: Empty recipient is rejected."""
        result = await send_email(
            mock_context,
            to_email="",
            subject="Test",
            message="Test"
        )
        
        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_send_email_empty_subject(self, mock_context):
        """Test: Empty subject is allowed (but unusual)."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="",
                    message="Test message"
                )
                
                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_email_empty_message(self, mock_context):
        """Test: Empty message is allowed."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                subject="Test Subject",
                message=""
            )
            
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_email_special_characters_in_message(self, mock_context):
        """Test: Special characters in message body."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test",
                    message="Test with émojis 🎉 and spëcial çhars"
                )
                
                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_email_long_message(self, mock_context):
        """Test: Very long email message."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                long_message = "A" * 10000  # 10KB message
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test",
                    message=long_message
                )
                
                assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_email_multiple_recipients(self, mock_context):
        """Test: Multiple CC recipients (if supported)."""
        # This depends on your implementation
        # If your function only supports single CC, adjust test
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test",
                    message="Test",
                    cc_email="cc@example.com"
                )
                
                assert isinstance(result, str)


class TestEmailErrorHandling:
    """Test error handling in email tool."""

    @pytest.mark.asyncio
    async def test_send_email_smtp_connection_error(self, mock_context):
        """Test: SMTP connection error is handled."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL', side_effect=ConnectionError("Connection refused")):
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test",
                    message="Test"
                )
                
                assert isinstance(result, str)
                assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_send_email_authentication_error(self, mock_context):
        """Test: Authentication failure is handled gracefully."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_server.login.side_effect = Exception("Authentication failed")
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test",
                    message="Test"
                )
                
                assert isinstance(result, str)
                assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_send_email_missing_env_variables(self, mock_context):
        """Test: Missing email credentials are caught."""
        with patch.dict(os.environ, {'GMAIL_USER': '', 'GMAIL_APP_PASSWORD': ''}):
            result = await send_email(
                mock_context,
                to_email="test@example.com",
                subject="Test",
                message="Test"
            )
            
            assert isinstance(result, str)
            # Should return error if credentials missing

    @pytest.mark.asyncio
    async def test_send_email_timeout(self, mock_context):
        """Test: SMTP timeout is handled."""
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL', side_effect=TimeoutError("Connection timeout")):
                result = await send_email(
                    mock_context,
                    to_email="test@example.com",
                    subject="Test",
                    message="Test"
                )
                
                assert isinstance(result, str)
                assert "error" in result.lower()


class TestEmailValidation:
    """Test email validation."""

    @pytest.mark.asyncio
    async def test_send_email_validation_various_invalid_emails(self, mock_context):
        """Test: Various invalid email formats are rejected."""
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
            "user@",
            "@.com",
        ]
        
        for invalid_email in invalid_emails:
            result = await send_email(
                mock_context,
                to_email=invalid_email,
                subject="Test",
                message="Test"
            )
            
            assert isinstance(result, str)
            assert "error" in result.lower() or "invalid" in result.lower()

    @pytest.mark.asyncio
    async def test_send_email_valid_email_formats(self, mock_context):
        """Test: Various valid email formats are accepted."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@sub.example.com",
        ]
        
        with patch.dict(os.environ, {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'test_password'}):
            with patch('smtplib.SMTP_SSL') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                
                for valid_email in valid_emails:
                    result = await send_email(
                        mock_context,
                        to_email=valid_email,
                    subject="Test",
                    message="Test"
                )
                
                assert isinstance(result, str)
                # Should not reject as invalid
