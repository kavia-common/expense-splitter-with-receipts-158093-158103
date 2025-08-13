from decimal import Decimal
from typing import Dict

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..models import Group, Expense, User


blp = Blueprint(
    "Balances",
    __name__,
    url_prefix="/groups/<int:group_id>/balances",
    description="Compute outstanding balances within a group.",
)


def _user_public(user: User) -> Dict:
    return {"id": user.id, "name": user.name, "email": user.email}


@blp.route("")
class GroupBalances(MethodView):
    """Compute per-user balances for a group."""

    # PUBLIC_INTERFACE
    @blp.response(200)
    @blp.doc(
        summary="Get group balances",
        description="Compute net balances for all users in the group. Positive balance means the user is owed money; negative means they owe money. Settled shares are excluded.",
        tags=["Balances"],
    )
    def get(self, group_id: int):
        """Return balances per user for the group."""
        group = Group.query.get(group_id)
        if not group:
            abort(404, message="Group not found")

        net: Dict[int, Decimal] = {}

        expenses = Expense.query.filter_by(group_id=group_id).all()
        for exp in expenses:
            amount = Decimal(exp.amount or 0)
            if exp.paid_by_user_id:
                net[exp.paid_by_user_id] = net.get(exp.paid_by_user_id, Decimal("0")) + amount
            # Subtract only unsettled shares
            for sh in exp.shares:
                if not sh.is_settled:
                    net[sh.user_id] = net.get(sh.user_id, Decimal("0")) - Decimal(sh.amount or 0)

        # Prepare response objects with user info
        user_ids = set(net.keys())
        users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        result = []
        for uid, balance in net.items():
            user = users.get(uid)
            result.append(
                {
                    "user": _user_public(user) if user else {"id": uid},
                    "balance": str(balance.quantize(Decimal("0.01"))),
                }
            )

        return {"group_id": group_id, "balances": result}
