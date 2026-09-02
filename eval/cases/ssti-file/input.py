from flask import request, render_template_string

GREETING = "<h1>Hello {name}, welcome to {tenant}</h1>"


def tenant_greeting():
    """Render a tenant's customized greeting banner."""
    template = GREETING.replace("{tenant}", request.args["tenant_banner"])
    return render_template_string(template, name=request.args.get("name", ""))
