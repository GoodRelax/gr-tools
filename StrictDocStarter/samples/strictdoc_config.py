# StrictDoc project configuration.
#
# This file must live in the folder that is passed to `strictdoc server <path>`.
# In StrictDocStarter that path is `project_path` in server.config.json, which
# points to this `samples\` directory -- so this file belongs here.
#
# The "MERMAID" feature is REQUIRED for StrictDoc to load mermaid.min.js and
# render <pre class="mermaid"> blocks (e.g. samples/hello-strictdoc/04-mermaid.sdoc)
# as diagrams. Without it the diagram stays plain text.
#
# Docs: https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html
#       (section "Mermaid diagramming and charting tool")
from strictdoc.core.project_config import ProjectConfig


def create_config() -> ProjectConfig:
    return ProjectConfig(
        project_title="StrictDocStarter Samples",
        project_features=[
            "MERMAID",
        ],
    )
