from flask_smorest import Blueprint
from flask.views import MethodView

# Define a proper blueprint name and import_name for clean OpenAPI tags
blp = Blueprint("Health", __name__, url_prefix="/", description="Health check route")

@blp.route("/")
class HealthCheck(MethodView):
    """Health check endpoint to verify that the API service is running."""
    # PUBLIC_INTERFACE
    @blp.response(200)
    @blp.doc(
        summary="Health check",
        description="Returns a simple status indicating that the API is healthy.",
        tags=["Health"],
    )
    def get(self):
        """Return a health status response."""
        return {"message": "Healthy"}
