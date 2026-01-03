"""
ChainShield Email Service

Send transactional emails:
- Welcome / verification
- Password reset
- Risk alerts
- Usage warnings

Supports SendGrid, SES, or SMTP.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import structlog

logger = structlog.get_logger()


@dataclass
class EmailMessage:
    """Email message to send."""
    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None


class EmailService:
    """
    Email service for transactional emails.
    
    Usage:
        email = get_email_service()
        
        await email.send_verification(
            to="user@example.com",
            token="abc123"
        )
    """
    
    def __init__(self):
        self.logger = logger.bind(module="email_service")
        
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_FROM", "noreply@chainshield.io")
        self.from_name = os.getenv("SMTP_FROM_NAME", "ChainShield")
        self.app_url = os.getenv("APP_URL", "https://app.chainshield.io")
        
        self._is_configured = bool(self.smtp_password)
    
    async def send(self, message: EmailMessage) -> bool:
        """
        Send an email message.
        
        Returns True if sent successfully.
        """
        if not self._is_configured:
            self.logger.warning("email_not_configured", to=message.to)
            return False
        
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.subject
            msg["From"] = f"{message.from_name or self.from_name} <{message.from_email or self.from_email}>"
            msg["To"] = message.to
            
            if message.text_body:
                msg.attach(MIMEText(message.text_body, "plain"))
            msg.attach(MIMEText(message.html_body, "html"))
            
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=True
            )
            
            self.logger.info("email_sent", to=message.to, subject=message.subject)
            return True
            
        except ImportError:
            self.logger.warning("aiosmtplib_not_installed")
            return False
        except Exception as e:
            self.logger.error("email_send_failed", to=message.to, error=str(e))
            return False
    
    # =========================================================================
    # Pre-built email templates
    # =========================================================================
    
    async def send_verification(self, to: str, token: str) -> bool:
        """Send email verification link."""
        verify_url = f"{self.app_url}/verify?token={token}"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #0891b2;">Welcome to ChainShield</h1>
            <p>Thank you for registering! Please verify your email address by clicking the button below:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" 
                   style="background: linear-gradient(135deg, #06b6d4, #3b82f6);
                          color: white;
                          padding: 12px 32px;
                          text-decoration: none;
                          border-radius: 8px;
                          font-weight: bold;">
                    Verify Email
                </a>
            </p>
            <p style="color: #666; font-size: 12px;">
                This link expires in 24 hours. If you didn't create an account, ignore this email.
            </p>
        </div>
        """
        
        return await self.send(EmailMessage(
            to=to,
            subject="Verify your ChainShield account",
            html_body=html,
            text_body=f"Verify your email: {verify_url}"
        ))
    
    async def send_password_reset(self, to: str, token: str) -> bool:
        """Send password reset link."""
        reset_url = f"{self.app_url}/reset-password?token={token}"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #0891b2;">Reset Your Password</h1>
            <p>We received a request to reset your password. Click the button below to continue:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background: linear-gradient(135deg, #06b6d4, #3b82f6);
                          color: white;
                          padding: 12px 32px;
                          text-decoration: none;
                          border-radius: 8px;
                          font-weight: bold;">
                    Reset Password
                </a>
            </p>
            <p style="color: #666; font-size: 12px;">
                This link expires in 1 hour. If you didn't request this, ignore this email.
            </p>
        </div>
        """
        
        return await self.send(EmailMessage(
            to=to,
            subject="Reset your ChainShield password",
            html_body=html,
            text_body=f"Reset your password: {reset_url}"
        ))
    
    async def send_risk_alert(
        self,
        to: str,
        address: str,
        risk_score: float,
        risk_level: str,
        chain: str = "ethereum"
    ) -> bool:
        """Send high-risk alert notification."""
        color = "#ef4444" if risk_level == "CRITICAL" else "#f59e0b"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: {color};">⚠️ Risk Alert: {risk_level}</h1>
            <div style="background: #1e293b; padding: 20px; border-radius: 8px; color: white;">
                <p><strong>Address:</strong> {address}</p>
                <p><strong>Chain:</strong> {chain.upper()}</p>
                <p><strong>Risk Score:</strong> {risk_score:.1f}/100</p>
                <p><strong>Risk Level:</strong> <span style="color: {color};">{risk_level}</span></p>
            </div>
            <p style="margin-top: 20px;">
                <a href="{self.app_url}/address/{address}" 
                   style="color: #06b6d4;">View Full Analysis →</a>
            </p>
        </div>
        """
        
        return await self.send(EmailMessage(
            to=to,
            subject=f"[{risk_level}] Risk Alert: {address[:16]}...",
            html_body=html,
            text_body=f"Risk Alert: {address} - Score: {risk_score} - Level: {risk_level}"
        ))
    
    async def send_usage_warning(
        self,
        to: str,
        usage_percent: float,
        tier: str
    ) -> bool:
        """Send usage warning (80% threshold)."""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #f59e0b;">Usage Warning</h1>
            <p>You've used <strong>{usage_percent:.0f}%</strong> of your monthly quota on your <strong>{tier}</strong> plan.</p>
            <p>Consider upgrading to avoid service interruption:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{self.app_url}/billing" 
                   style="background: linear-gradient(135deg, #06b6d4, #3b82f6);
                          color: white;
                          padding: 12px 32px;
                          text-decoration: none;
                          border-radius: 8px;
                          font-weight: bold;">
                    Upgrade Plan
                </a>
            </p>
        </div>
        """
        
        return await self.send(EmailMessage(
            to=to,
            subject="ChainShield: Usage Warning",
            html_body=html,
            text_body=f"Usage Warning: You've used {usage_percent:.0f}% of your monthly quota."
        ))


# Singleton
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
