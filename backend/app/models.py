from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from . import db


class User(db.Model):
    """Represents a user/friend in the expense splitting system."""
    __tablename__ = "users"
    # Allow legacy annotations without SQLAlchemy 2.0 Mapped[] wrappers
    __allow_unmapped__ = True

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(120), nullable=False)
    email: Optional[str] = db.Column(db.String(255), unique=True, nullable=True)
    phone: Optional[str] = db.Column(db.String(50), nullable=True)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    groups_created = db.relationship("Group", back_populates="created_by", lazy="select")
    expenses_paid = db.relationship(
        "Expense",
        back_populates="paid_by_user",
        foreign_keys="Expense.paid_by_user_id",
        lazy="select",
    )
    group_memberships = db.relationship("GroupMember", back_populates="user", lazy="select")
    expense_shares = db.relationship("ExpenseShare", back_populates="user", lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r}>"


class Group(db.Model):
    """Represents a group to which users can belong and record expenses."""
    __tablename__ = "groups"
    __allow_unmapped__ = True

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(150), nullable=False)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    created_by_user_id: int = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    created_by = db.relationship("User", back_populates="groups_created", lazy="joined")
    members: List["GroupMember"] = db.relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="select",
    )
    expenses: List["Expense"] = db.relationship(
        "Expense",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"


class GroupMember(db.Model):
    """Association table for group memberships between users and groups."""
    __tablename__ = "group_members"
    __allow_unmapped__ = True
    __table_args__ = (
        db.UniqueConstraint("group_id", "user_id", name="uq_group_member_group_user"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    group_id: int = db.Column(
        db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: int = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Optional[str] = db.Column(db.String(50), nullable=True)  # e.g., "admin", "member"
    joined_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    group = db.relationship("Group", back_populates="members", lazy="joined")
    user = db.relationship("User", back_populates="group_memberships", lazy="joined")

    def __repr__(self) -> str:
        return f"<GroupMember group_id={self.group_id} user_id={self.user_id}>"


class Expense(db.Model):
    """Represents an expense within a group, optionally associated with a receipt image."""
    __tablename__ = "expenses"
    __allow_unmapped__ = True

    id: int = db.Column(db.Integer, primary_key=True)
    group_id: int = db.Column(
        db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    paid_by_user_id: int = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    description: str = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    expense_date: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Receipt fields: Only the filename is stored, paths handled by storage utils
    receipt_filename: Optional[str] = db.Column(db.String(255), nullable=True)
    receipt_mime_type: Optional[str] = db.Column(db.String(100), nullable=True)

    created_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at: datetime = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    group = db.relationship("Group", back_populates="expenses", lazy="joined")
    paid_by_user = db.relationship(
        "User", back_populates="expenses_paid", foreign_keys=[paid_by_user_id], lazy="joined"
    )
    shares: List["ExpenseShare"] = db.relationship(
        "ExpenseShare",
        back_populates="expense",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Expense id={self.id} amount={self.amount} desc={self.description!r}>"


class ExpenseShare(db.Model):
    """Represents a share of an expense assigned to a particular user."""
    __tablename__ = "expense_shares"
    __allow_unmapped__ = True
    __table_args__ = (
        db.UniqueConstraint("expense_id", "user_id", name="uq_expense_share_expense_user"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    expense_id: int = db.Column(
        db.Integer, db.ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: int = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    is_settled: bool = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    expense = db.relationship("Expense", back_populates="shares", lazy="joined")
    user = db.relationship("User", back_populates="expense_shares", lazy="joined")

    def __repr__(self) -> str:
        return f"<ExpenseShare expense_id={self.expense_id} user_id={self.user_id} amount={self.amount}>"
