from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from . import db
from .models import User, Group, GroupMember, Expense, ExpenseShare


class UserSchema(SQLAlchemyAutoSchema):
    """Schema for serializing and deserializing User instances."""

    class Meta:
        model = User
        sqla_session = db.session
        load_instance = True
        include_fk = True
        include_relationships = False

    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class GroupSchema(SQLAlchemyAutoSchema):
    """Schema for serializing and deserializing Group instances."""

    class Meta:
        model = Group
        sqla_session = db.session
        load_instance = True
        include_fk = True
        include_relationships = True

    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    created_by = fields.Nested(UserSchema, only=("id", "name", "email"), dump_only=True)


class GroupMemberSchema(SQLAlchemyAutoSchema):
    """Schema for serializing and deserializing GroupMember instances."""

    class Meta:
        model = GroupMember
        sqla_session = db.session
        load_instance = True
        include_fk = True
        include_relationships = True

    id = fields.Int(dump_only=True)
    joined_at = fields.DateTime(dump_only=True)
    user = fields.Nested(UserSchema, only=("id", "name", "email"), dump_only=True)
    group = fields.Nested(GroupSchema, only=("id", "name"), dump_only=True)


class ExpenseShareSchema(SQLAlchemyAutoSchema):
    """Schema for serializing and deserializing ExpenseShare instances."""

    class Meta:
        model = ExpenseShare
        sqla_session = db.session
        load_instance = True
        include_fk = True
        include_relationships = True

    id = fields.Int(dump_only=True)
    user = fields.Nested(UserSchema, only=("id", "name", "email"), dump_only=True)
    amount = fields.Decimal(as_string=True)
    is_settled = fields.Bool()


class ExpenseSchema(SQLAlchemyAutoSchema):
    """Schema for serializing and deserializing Expense instances."""

    class Meta:
        model = Expense
        sqla_session = db.session
        load_instance = True
        include_fk = True
        include_relationships = True

    id = fields.Int(dump_only=True)
    amount = fields.Decimal(as_string=True)
    expense_date = fields.DateTime()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    paid_by_user = fields.Nested(UserSchema, only=("id", "name", "email"), dump_only=True)
    shares = fields.Nested(ExpenseShareSchema, many=True, dump_only=True)
    group = fields.Nested(GroupSchema, only=("id", "name"), dump_only=True)
    receipt_filename = fields.String(allow_none=True)
    receipt_mime_type = fields.String(allow_none=True)
