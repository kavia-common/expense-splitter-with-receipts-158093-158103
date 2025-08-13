from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate

from .. import db
from ..models import Group, GroupMember, User
from ..schemas import GroupMemberSchema


class MemberCreateSchema(Schema):
    user_id = fields.Integer(required=True, description="ID of existing user to add to the group")
    role = fields.String(allow_none=True, validate=validate.Length(max=50), description="Optional role for the member")


class MemberUpdateSchema(Schema):
    role = fields.String(required=True, validate=validate.Length(max=50), description="New role to set for the member")


blp = Blueprint(
    "Members",
    __name__,
    url_prefix="/groups/<int:group_id>/members",
    description="Manage group memberships.",
)


@blp.route("")
class GroupMembersCollection(MethodView):
    """List and add members to a group."""

    # PUBLIC_INTERFACE
    @blp.response(200, GroupMemberSchema(many=True))
    @blp.doc(summary="List group members", description="List all members of the specified group.")
    def get(self, group_id: int):
        """Return all members for the group."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")
        members = GroupMember.query.filter_by(group_id=group_id).all()
        return members

    # PUBLIC_INTERFACE
    @blp.arguments(MemberCreateSchema)
    @blp.response(201, GroupMemberSchema)
    @blp.doc(summary="Add member", description="Add an existing user to the group.")
    def post(self, data, group_id: int):
        """Add a user to the group."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")

        user = User.query.get(data["user_id"])
        if not user:
            abort(400, message="User not found")

        existing = GroupMember.query.filter_by(group_id=group_id, user_id=user.id).first()
        if existing:
            abort(409, message="User is already a member of the group")

        gm = GroupMember(group_id=group_id, user_id=user.id, role=data.get("role"))
        db.session.add(gm)
        db.session.commit()
        return gm


@blp.route("/<int:member_id>")
class GroupMemberItem(MethodView):
    """Update or remove a specific group member."""

    # PUBLIC_INTERFACE
    @blp.response(200, GroupMemberSchema)
    @blp.doc(summary="Get member", description="Retrieve a specific group membership by id.")
    def get(self, group_id: int, member_id: int):
        """Get a group member by id."""
        gm = GroupMember.query.filter_by(id=member_id, group_id=group_id).first()
        if not gm:
            abort(404, message="Group member not found")
        return gm

    # PUBLIC_INTERFACE
    @blp.arguments(MemberUpdateSchema)
    @blp.response(200, GroupMemberSchema)
    @blp.doc(summary="Update member", description="Update a group member's role.")
    def patch(self, data, group_id: int, member_id: int):
        """Update a group member (role)."""
        gm = GroupMember.query.filter_by(id=member_id, group_id=group_id).first()
        if not gm:
            abort(404, message="Group member not found")
        gm.role = data["role"]
        db.session.commit()
        return gm

    # PUBLIC_INTERFACE
    @blp.response(204)
    @blp.doc(summary="Remove member", description="Remove a member from the group.")
    def delete(self, group_id: int, member_id: int):
        """Remove a user from the group."""
        gm = GroupMember.query.filter_by(id=member_id, group_id=group_id).first()
        if not gm:
            abort(404, message="Group member not found")
        db.session.delete(gm)
        db.session.commit()
        return ""
