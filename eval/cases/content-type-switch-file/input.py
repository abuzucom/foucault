import json
from defusedxml import ElementTree as SafeET
import xml.etree.ElementTree as ET


def parse_body(request):
    """Accept either JSON or XML from integration partners."""
    body = request.body
    if body.lstrip().startswith(b"<"):
        return ET.fromstring(body)
    return json.loads(body)
