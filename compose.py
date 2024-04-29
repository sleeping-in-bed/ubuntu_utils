from pathlib import Path
from psplpy.dynamic_compose import DynamicCompose
dc = DynamicCompose()

dc.format_compose(template_file=(Path(__file__).parent / 'compose-template.yml'))
dc.format_dockerfile(template_file=(Path(__file__).parent / 'Dockerfile-template'))
dc.dump()
dc.up()
