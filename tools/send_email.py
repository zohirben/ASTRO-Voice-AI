# See /docs_imported/agents/tools.md - Function tool patterns for email functionality
from livekit.agents import function_tool, RunContext
import logging
import os
import smtplib
import asyncio
import contextlib
import re
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional

# Email validation regex - RFC 5322 simplified
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Email sending timeout constant
EMAIL_TIMEOUT = 15.0

# See https://docs.livekit.io/agents/build/external-data/#user-feedback - Status updates during long-running tools
STATUS_UPDATE_ENABLED = os.getenv("ENABLE_TOOL_STATUS_UPDATES", "false").lower() == "true"
try:
    STATUS_UPDATE_DELAY = float(os.getenv("TOOL_STATUS_UPDATE_DELAY", "1.5"))
except ValueError:
    STATUS_UPDATE_DELAY = 1.5
STATUS_UPDATE_PROMPT = os.getenv(
    "TOOL_STATUS_UPDATE_PROMPT",
    "Provide a very short status update that you are still working on the email request.",
)

@function_tool()    
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    For Realtime/Voice agents (like Gemini Realtime), this tool RETURNS error strings
    instead of raising exceptions. This allows Gemini to:
    1. See the actual error message in the return string
    2. Parse it against the "error" keyword check in prompts.py
    3. Voice the error correctly to the user
    
    See /docs_imported/agents/tools.md - Voice agent error handling patterns
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
        
    Returns:
        Success: "email sent successfully to [recipient]"
        Error: "error: [reason]" (allows Gemini to detect and voice the error)
    """
    logging.info(
        "send_email: status_update_enabled=%s, delay=%.2f",
        STATUS_UPDATE_ENABLED,
        STATUS_UPDATE_DELAY,
    )

    status_task: Optional[asyncio.Task] = None
    status_cancelled = asyncio.Event()
    if STATUS_UPDATE_ENABLED:
        status_task = asyncio.create_task(
            _delayed_status_update(context, STATUS_UPDATE_DELAY, status_cancelled)
        )

    try:
        # Wrap with EMAIL_TIMEOUT to prevent hanging
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, 
                _send_email_sync, 
                to_email, 
                subject, 
                message, 
                cc_email
            ),
            timeout=EMAIL_TIMEOUT
        )
        # For voice agents (Realtime models), return error strings instead of raising
        # This allows Gemini to see the actual error message and voice it correctly
        # See /docs_imported/agents/tools.md - Voice agent error handling patterns
        if isinstance(result, str) and result.lower().startswith("error:"):
            return result  # Return error string for Gemini to parse
        return result
    except asyncio.TimeoutError:
        logging.error(f"Email sending timed out after {EMAIL_TIMEOUT:.0f} seconds")
        # Return error string instead of raising - allows Gemini to voice the error
        return f"error: email sending timed out after {EMAIL_TIMEOUT:.0f} seconds"
    except Exception as e:
        logging.error(f"Unexpected error in send_email: {e}")
        # Return error string instead of raising - allows Gemini to voice the error
        return f"error: {str(e)}"
    finally:
        # Signal status update to stop before cancelling
        status_cancelled.set()
        if status_task:
            status_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await status_task


def _send_email_sync(
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """Synchronous email sending function."""
    # CRITICAL BUG #2 FIX: Proper email validation with regex
    # Instead of just checking "@", validate against RFC 5322 pattern
    if not to_email or not re.match(EMAIL_REGEX, to_email):
        return "error: invalid recipient email address"
    
    if cc_email and not re.match(EMAIL_REGEX, cc_email):
        return "error: invalid cc email address"
    
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 465  # Use SSL port for SMTP_SSL
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "error: gmail credentials not configured"
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Attach message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail SMTP server with timeout
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
            server.login(gmail_user, gmail_password)

            # Send email and check for any delivery failures
            text = msg.as_string()
            send_result = server.sendmail(gmail_user, recipients, text)

            # MINOR BUG #7 FIX: Simplify dict check - empty dict is falsy
            # smtplib.sendmail() returns empty dict {} on success, or dict with failed recipients
            if send_result:
                failed_recipients = ", ".join(send_result.keys())
                logging.error(f"Failed to deliver to: {failed_recipients}")
                return f"error: failed to deliver to {failed_recipients}"

            logging.info(f"Email sent successfully to {to_email}")
            return f"email sent successfully to {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "error: gmail authentication failed"
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return "error: smtp error occurred"
    except (OSError, smtplib.SMTPException) as e:
        logging.error(f"Email operation failed: {e}")
        return f"error: {str(e)}"


async def _delayed_status_update(context: RunContext, delay: float, cancel_event: asyncio.Event) -> None:
    """Emit a brief status update if the tool runs longer than the delay.
    
    Args:
        context: RunContext for session access
        delay: Seconds to wait before emitting status
        cancel_event: Event to signal early termination
    """
    try:
        logging.info("status_update: waiting %.2fs before speaking", delay)
        await asyncio.sleep(delay)
        
        # MEDIUM BUG #3 FIX: Check cancel_event before proceeding
        if cancel_event.is_set():
            logging.debug("status_update: cancelled before execution")
            return
        
        session = getattr(context, "session", None)
        if session is None:
            logging.info("status_update: no session on context; skipping")
            return
        speech_handle = getattr(context, "speech_handle", None)
        if speech_handle is not None:
            wait_playout = getattr(speech_handle, "wait_for_playout", None)
            if callable(wait_playout):
                logging.info("status_update: awaiting current speech playout")
                with contextlib.suppress(Exception):
                    await wait_playout()
            else:
                done_fn = getattr(speech_handle, "done", None)
                # MEDIUM BUG #4 FIX: Log warning if neither method available
                if done_fn is None:
                    logging.warning("status_update: no playout check available; proceeding anyway")
                elif callable(done_fn) and not done_fn():
                    logging.info("status_update: speech still active; skipping")
                    return
        logging.info("status_update: generating brief status reply")
        await session.generate_reply(instructions=STATUS_UPDATE_PROMPT)
        logging.info("status_update: status reply submitted")
    except asyncio.CancelledError:
        logging.debug("status_update: task cancelled")
        raise
    except Exception as exc:  # pragma: no cover - status updates are best effort
        logging.debug("Status update generation skipped: %s", exc)