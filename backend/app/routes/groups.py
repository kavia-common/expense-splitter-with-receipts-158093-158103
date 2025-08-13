
from typing import Optional

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate

from .. import db
from ..models import Group, User
from ..schemas import GroupSchema


class GroupCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=150), description="Group name")
    created_by_user_id = fields.Integer(allow_none=True, description="Optional user id who created the group")


class GroupUpdateSchema(Schema):
    name = fields.String(required=False, validate=validate.Length(min=1, max=150), description="Updated group name")


blp = Blueprint(
    "Groups",
    __name__,
    url_prefix="/groups",
    description="Endpoints to manage groups and their basic attributes.",
)


@blp.route("")
class GroupsCollection(MethodView):
    """List all groups and create new groups."""

    # PUBLIC_INTERFACE
    @blp.response(200, GroupSchema(many=True))
    @blp.doc(summary="List groups", description="Return all groups.", tags=["Groups"])
    def get(self):
        """Get all groups."""
        groups = Group.query.order_by(Group.created_at.desc()).all()
        return groups

    # PUBLIC_INTERFACE
    @blp.arguments(GroupCreateSchema)
    @blp.response(201, GroupSchema)
    @blp.doc(summary="Create group", description="Create a new group.", tags=["Groups"])
    def post(self, data):
        """Create a new group."""
        name = data["name"].strip()
        created_by_user_id: Optional[int] = data.get("created_by_user_id")

        created_by: Optional[User] = None
        if created_by_user_id is not None:
            created_by = User.query.get(created_by_user_id)
            if not created_by:
                abort(400, message="created_by_user_id does not reference an existing user")

        group = Group(name=name, created_by=created_by)
        db.session.add(group)
        db.session.commit()
        return group


@blp.route("/<int:group_id>")
class GroupItem(MethodView):
    """Retrieve, update, or delete a specific group by id."""

    # PUBLIC_INTERFACE
    @blp.response(200, GroupSchema)
    @blp.doc(summary="Get group", description="Retrieve a group by its id.", tags=["Groups"])
    def get(self, group_id: int):
        """Get a single group by id."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")
        return group

    # PUBLIC_INTERFACE
    @blp.arguments(GroupUpdateSchema)
    @blp.response(200, GroupSchema)
    @blp.doc(summary="Update group", description="Update the group's attributes.", tags=["Groups"])
    def patch(self, update_data, group_id: int):
        """Update a group's attributes."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")

        if "name" in update_data and update_data["name"]:
            group.name = update_data["name"].strip()

        db.session.commit()
        return group

    # PUBLIC_INTERFACE
    @blp.response(204)
    @blp.doc(summary="Delete group", description="Delete a group and its related data.", tags=["Groups"])
    def delete(self, group_id: int):
        """Delete a group by id."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")
        db.session.delete(group)
        db.session.commit()
        return ""
