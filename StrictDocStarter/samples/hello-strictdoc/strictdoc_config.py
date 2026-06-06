# StrictDoc project configuration for the bundled "hello-strictdoc" sample.
#
# IMPORTANT: this file MUST live in the folder passed to
# `strictdoc server <path>` / `strictdoc export <path>` -- i.e. the
# `project_path` in server.config.json. StrictDoc reads the config in the input
# folder ITSELF and does NOT look in parent folders (verified on strictdoc
# 0.23.1). That is why the config lives here, next to the .sdoc files.
#
# Shape follows the official `strictdoc new` output but enables MERMAID and
# MATHJAX so that this minimal "edit me" template already supports diagrams and
# math when you start adding your own. include_doc_paths / include_source_paths
# are omitted on purpose (flat layout, no docs/ or src/ subfolders).
#
# Docs: https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html
from strictdoc.core.project_config import ProjectConfig


def create_config() -> ProjectConfig:
    return ProjectConfig(
        project_title="Hello StrictDoc (StrictDocStarter sample)",
        project_features=[
            # Stable features (these four are strictdoc's defaults).
            "TABLE_SCREEN",
            "TRACEABILITY_SCREEN",
            "DEEP_TRACEABILITY_SCREEN",
            "SEARCH",
            # Stable. TeX/LaTeX math via RST .. math:: / :math:`...`.
            "MATHJAX",
            # Experimental. Mermaid diagrams (RST raw-html <pre class="mermaid">
            # and, on strictdoc 0.23.0+, Markdown ```mermaid fences).
            "MERMAID",
        ],
    )
