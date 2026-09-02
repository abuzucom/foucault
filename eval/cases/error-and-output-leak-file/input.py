def update_profile(request):
    try:
        payload = Profile.schema.load(request.json)
    except ValidationError as exc:
        return jsonify({
            "error": "validation failed",
            "detail": str(exc),
            "column": exc.field_name,
            "query": exc.statement,
        }), 400
    user = Profile.objects.get(id=request.user.id)
    user.update(**payload)
    return jsonify(user.to_dict())
