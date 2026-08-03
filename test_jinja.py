from jinja2 import Environment, FileSystemLoader
import json

env = Environment(trim_blocks=True, lstrip_blocks=True)
template = env.from_string("""
Glossary Terms:
{% for term in matched_terms %}
- "{{ term.source }}" -> "{{ term.target }}" [Category: {{ term.category }}]{% if term.notes %} (Notes: {{ term.notes }}){% endif %}

{% endfor %}

Characters in this chapter:
{% for char in matched_characters %}
- **{{ char.canonical_name }}**
  {% if char.appearance %}  Appearance: {{ char.appearance }}{% endif %}
  {% if char.notes %}  Notes: {{ char.notes }}{% endif %}

{% endfor %}
""")

print(template.render(
    matched_terms=[
        {"source": "A", "target": "A", "category": "item", "notes": "note A"},
        {"source": "B", "target": "B", "category": "item", "notes": "note B"}
    ],
    matched_characters=[
        {"canonical_name": "Char A", "appearance": "App A", "notes": "Note A"},
        {"canonical_name": "Char B", "appearance": "App B", "notes": "Note B"}
    ]
))
