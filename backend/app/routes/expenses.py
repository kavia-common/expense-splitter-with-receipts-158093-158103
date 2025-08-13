from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import List, Optional

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from .. import db
from ..models import Expense, ExpenseShare, Group, GroupMember
from ..schemas import ExpenseSchema, ExpenseShareSchema


def _to_decimal(value) -> Decimal:
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except Exception:
        raise ValidationError("Invalid decimal value")


class ShareInputSchema(Schema):
    user_id = fields.Integer(required=True, description="User id for this share")
    amount = fields.Decimal(as_string=True, required=True, description="Amount for this user's share")


class ExpenseCreateSchema(Schema):
    description = fields.String(required=True, validate=validate.Length(min=1, max=255))
    amount = fields.Decimal(as_string=True, required=True)
    paid_by_user_id = fields.Integer(allow_none=True)
    expense_date = fields.DateTime(allow_none=True)
    shares = fields.List(fields.Nested(ShareInputSchema), required=False)

    @validates_schema
    def validate_shares(self, data, **kwargs):
        shares = data.get("shares")
        if shares is None:
            return
        # Validate positive amounts
        for s in shares:
            if _to_decimal(s["amount"]) <= Decimal("0"):
                raise ValidationError("Share amount must be positive", field_name="shares")


class ExpenseUpdateSchema(Schema):
    description = fields.String(required=False, validate=validate.Length(min=1, max=255))
    amount = fields.Decimal(as_string=True, required=False)
    paid_by_user_id = fields.Integer(allow_none=True, required=False)
    expense_date = fields.DateTime(allow_none=True, required=False)
    shares = fields.List(fields.Nested(ShareInputSchema), required=False)


blp = Blueprint(
    "Expenses",
    __name__,
    url_prefix="",
    description="Manage expenses within groups, including shares logic.",
)


def _ensure_user_in_group(group_id: int, user_id: Optional[int]) -> None:
    if user_id is None:
        return
    member = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
    if not member:
        abort(400, message="paid_by_user_id must be a member of the group")


def _equal_split(amount: Decimal, user_ids: List[int]) -> List[ExpenseShare]:
    n = len(user_ids)
    if n == 0:
        abort(400, message="Cannot split expense: the group has no members")
    # Round down each share to 2 decimals, spread the remainder
    base = (amount / n).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    shares: List[ExpenseShare] = []
    subtotal = base * n
    remainder_cents = int((amount - subtotal) * 100)

    for idx, uid in enumerate(user_ids):
        share_amount = base
        if remainder_cents > 0:
            share_amount = (base + Decimal("0.01"))
            remainder_cents -= 1
        shares.append(ExpenseShare(user_id=uid, amount=share_amount))
    return shares


def _replace_shares(expense: Expense, new_shares: List[dict]) -> None:
    amount = Decimal(expense.amount)
    shares_objs: List[ExpenseShare] = []
    if new_shares is None:
        # No shares provided -> equal split among current members of the group
        member_ids = [gm.user_id for gm in GroupMember.query.filter_by(group_id=expense.group_id).all()]
        shares_objs = _equal_split(amount, member_ids)
    else:
        total = Decimal("0")
        for s in new_shares:
            uid = int(s["user_id"])
            amt = _to_decimal(s["amount"]).quantize(Decimal("0.01"))
            # ensure user is part of group
            if not GroupMember.query.filter_by(group_id=expense.group_id, user_id=uid).first():
                abort(400, message=f"user_id {uid} is not a member of the group")
            shares_objs.append(ExpenseShare(user_id=uid, amount=amt))
            total += amt
        if total != amount:
            abort(400, message="Sum of shares must equal the expense amount")

    # Replace existing shares
    for old in list(expense.shares):
        db.session.delete(old)
    for new in shares_objs:
        new.expense = expense
        db.session.add(new)


@blp.route("/groups/<int:group_id>/expenses")
class GroupExpensesCollection(MethodView):
    """List and create expenses for a group."""

    # PUBLIC_INTERFACE
    @blp.response(200, ExpenseSchema(many=True))
    @blp.doc(
        summary="List group expenses",
        description="List all expenses belonging to the specified group.",
        tags=["Expenses"],
    )
    def get(self, group_id: int):
        """List expenses for a group."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")
        expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.expense_date.desc()).all()
        return expenses

    # PUBLIC_INTERFACE
    @blp.arguments(ExpenseCreateSchema)
    @blp.response(201, ExpenseSchema)
    @blp.doc(
        summary="Create expense",
        description="Create a new expense within the group. If shares aren't provided, the amount is split equally among members.",
        tags=["Expenses"],
    )
    def post(self, data, group_id: int):
        """Create an expense in the group."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")

        amount = _to_decimal(data["amount"]).quantize(Decimal("0.01"))
        description = data["description"].strip()
        paid_by_user_id: Optional[int] = data.get("paid_by_user_id")
        _ensure_user_in_group(group_id, paid_by_user_id)

        expense_date: Optional[datetime] = data.get("expense_date")

        expense = Expense(
            group_id=group_id,
            description=description,
            amount=amount,
            paid_by_user_id=paid_by_user_id,
            expense_date=expense_date or datetime.utcnow(),
        )
        db.session.add(expense)
        db.session.flush()  # to get expense.id

        _replace_shares(expense, data.get("shares"))
        db.session.commit()
        return expense


@blp.route("/expenses/<int:expense_id>")
class ExpenseItem(MethodView):
    """Retrieve, update, or delete a single expense."""

    # PUBLIC_INTERFACE
    @blp.response(200, ExpenseSchema)
    @blp.doc(summary="Get expense", description="Get expense details.", tags=["Expenses"])
    def get(self, expense_id: int):
        """Get a single expense."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")
        return expense

    # PUBLIC_INTERFACE
    @blp.arguments(ExpenseUpdateSchema)
    @blp.response(200, ExpenseSchema)
    @blp.doc(
        summary="Update expense",
        description="Update expense fields. If shares are provided, they will replace existing shares.",
        tags=["Expenses"],
    )
    def patch(self, data, expense_id: int):
        """Update an expense."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")

        if "description" in data and data["description"]:
            expense.description = data["description"].strip()

        if "paid_by_user_id" in data:
            _ensure_user_in_group(expense.group_id, data.get("paid_by_user_id"))
            expense.paid_by_user_id = data.get("paid_by_user_id")

        if "expense_date" in data and data["expense_date"]:
            expense.expense_date = data["expense_date"]

        shares_input = data.get("shares")

        if "amount" in data and data["amount"] is not None:
            new_amount = _to_decimal(data["amount"]).quantize(Decimal("0.01"))
            expense.amount = new_amount
            # If amount changed and no shares supplied, recompute equal split
            if shares_input is None:
                _replace_shares(expense, None)

        if shares_input is not None:
            _replace_shares(expense, shares_input)

        db.session.commit()
        return expense

    # PUBLIC_INTERFACE
    @blp.response(204)
    @blp.doc(summary="Delete expense", description="Delete an expense and its shares.", tags=["Expenses"])
    def delete(self, expense_id: int):
        """Delete an expense."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")
        db.session.delete(expense)
        db.session.commit()
        return ""


@blp.route("/expenses/<int:expense_id>/shares/<int:share_id>/settle")
class ExpenseShareSettle(MethodView):
    """Mark an expense share as settled."""

    # PUBLIC_INTERFACE
    @blp.response(200, ExpenseShareSchema)
    @blp.doc(
        summary="Settle share",
        description="Mark a specific expense share as settled.",
        tags=["Expenses"],
    )
    def post(self, expense_id: int, share_id: int):
        """Mark a share as settled."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")
        share = ExpenseShare.query.filter_by(id=share_id, expense_id=expense_id).first()
        if not share:
            abort(404, message="Expense share not found")
        share.is_settled = True
        db.session.commit()
        return share
