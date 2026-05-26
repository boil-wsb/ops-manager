from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


def set_request_context(request_id="", user_id=""):
    request_id_ctx.set(request_id)
    user_id_ctx.set(user_id)


def clear_request_context():
    request_id_ctx.set("")
    user_id_ctx.set("")
