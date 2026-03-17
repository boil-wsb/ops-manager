"""
Audit log model for tracking user operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, DateTime, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AuditLog(Base):
    """
    Audit log model for tracking all critical operations.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Operation info
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """Type of operation: LOGIN, LOGOUT, CREATE, UPDATE, DELETE, EXPORT"""
    
    operation_module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """Module: asset, user, role, monitor, certificate, deploy, system"""
    
    object_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Type of object being operated on: Asset, User, Role, etc."""
    
    object_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    """ID of the object being operated on"""
    
    object_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    """Name of the object for display purposes"""
    
    # Data snapshots
    before_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    """Data before operation (for UPDATE/DELETE)"""
    
    after_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    """Data after operation (for CREATE/UPDATE)"""
    
    # Operator info
    operator_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    """ID of the user performing the operation"""
    
    operator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Username of the operator"""
    
    operator_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """IP address of the operator"""
    
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """User agent string"""
    
    # Operation details
    operation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    """Timestamp of the operation"""
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    """Operation status: SUCCESS or FAILURE"""
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Error message if operation failed"""
    
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    """Request ID for tracing"""
    
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Operation duration in milliseconds"""
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_logs_module_time', 'operation_module', 'operation_time'),
        Index('idx_audit_logs_operator_time', 'operator_id', 'operation_time'),
        Index('idx_audit_logs_type_time', 'operation_type', 'operation_time'),
        Index('idx_audit_logs_status_time', 'status', 'operation_time'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, "
            f"type={self.operation_type}, "
            f"module={self.operation_module}, "
            f"object={self.object_type}:{self.object_id}, "
            f"operator={self.operator_name}, "
            f"status={self.status}, "
            f"time={self.operation_time})>"
        )
