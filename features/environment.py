# features/environment.py
import os


def before_all(context):
    # behave -D base_url=http://host:port OR export BASE_URL before running
    context.base_url = (
        getattr(context.config.userdata, "base_url", None)
        or os.getenv("BASE_URL")
        or "http://localhost:5001"
    )
