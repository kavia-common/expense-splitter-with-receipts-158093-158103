import os
from flask import send_file, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from werkzeug.datastructures import FileStorage

from .. import db
from ..models import Expense
from ..utils.storage import save_receipt_file, get_receipt_path
from ..schemas import ExpenseSchema

blp = Blueprint(
    "Receipts",
    __name__,
    url_prefix="/expenses/<int:expense_id>/receipt",
    description="Upload, download, and delete receipt files for expenses.",
)


@blp.route("")
class ExpenseReceipt(MethodView):
    """Manage a single expense's receipt."""

    # PUBLIC_INTERFACE
    @blp.response(200)
    @blp.doc(
        summary="Download receipt",
        description="Return the receipt file for the given expense, if present.",
        tags=["Receipts"],
    )
    def get(self, expense_id: int):
        """Download the receipt for the expense."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")
        if not expense.receipt_filename:
            abort(404, message="No receipt attached to this expense")

        filepath = get_receipt_path(expense.receipt_filename)
        if not os.path.exists(filepath):
            abort(404, message="Receipt file not found on disk")

        return send_file(filepath, mimetype=expense.receipt_mime_type or "application/octet-stream")

    # PUBLIC_INTERFACE
    @blp.response(200, ExpenseSchema)
    @blp.doc(
        summary="Upload/replace receipt",
        description="Upload or replace the receipt image/file for an expense (multipart/form-data with field name 'file').",
        tags=["Receipts"],
    )
    def post(self, expense_id: int):
        """Upload a new receipt file for an expense (replaces existing if any)."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")

        if "file" not in request.files:
            abort(400, message="No file part in the request")
        file: FileStorage = request.files["file"]
        if file.filename == "":
            abort(400, message="No selected file")

        try:
            filename = save_receipt_file(file)
        except ValueError as e:
            abort(400, message=str(e))

        # Remove previous file if present
        if expense.receipt_filename:
            try:
                old_path = get_receipt_path(expense.receipt_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                # Best-effort cleanup; don't block on errors
                pass

        expense.receipt_filename = filename
        expense.receipt_mime_type = file.mimetype or None
        db.session.commit()
        return expense

    # PUBLIC_INTERFACE
    @blp.response(200, ExpenseSchema)
    @blp.doc(
        summary="Delete receipt",
        description="Delete the receipt associated with the expense and clear its fields.",
        tags=["Receipts"],
    )
    def delete(self, expense_id: int):
        """Delete the receipt file and clear the expense's receipt fields."""
        expense = Expense.query.get(expense_id)
        if not expense:
            abort(404, message="Expense not found")

        if not expense.receipt_filename:
            abort(404, message="No receipt attached to this expense")

        try:
            path = get_receipt_path(expense.receipt_filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            # Ignore file errors; we'll still clear DB fields
            pass

        expense.receipt_filename = None
        expense.receipt_mime_type = None
        db.session.commit()
        return expense
