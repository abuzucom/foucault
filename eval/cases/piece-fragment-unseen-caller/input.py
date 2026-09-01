def render_snippet(template_name, values):
    template = env.get_template(template_name)
    return template.render(**values)
