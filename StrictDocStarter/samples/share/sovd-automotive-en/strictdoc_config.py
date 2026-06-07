# StrictDoc project configuration for the bundled "sovd-automotive" sample.
#
# IMPORTANT: this file MUST live in the folder passed to
# `strictdoc server <path>` / `strictdoc export <path>` -- i.e. the
# `project_path` in server.config.json. StrictDoc reads the config in the input
# folder ITSELF and does NOT look in parent folders (verified on strictdoc
# 0.23.1). That is why the config lives here, next to the .sdoc files, and not
# in the StrictDocStarter tool root.
#
# Shape follows the official `strictdoc new` output (create_config() returning a
# ProjectConfig with a project_features toggle list) but additionally enables
# MERMAID and MATHJAX, which `strictdoc new` leaves off. include_doc_paths /
# include_source_paths are intentionally omitted: this sample keeps its .sdoc
# files flat in this folder (no docs/ or src/ subfolders), so the default
# "scan everything under the project" behaviour is what we want.
#
# Docs: https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html
#       (sections "Selecting features", "Mermaid diagramming and charting tool")
from strictdoc.core.project_config import ProjectConfig


def create_config() -> ProjectConfig:
    return ProjectConfig(
        project_title="SOVD Automotive EN (StrictDocStarter sample)",
        project_features=[
            # Stable features (these four are strictdoc's defaults).
            "TABLE_SCREEN",
            "TRACEABILITY_SCREEN",
            "DEEP_TRACEABILITY_SCREEN",
            "SEARCH",
            # Stable. Enabled for the math (.. math:: / :math:) in 01-auth.sdoc.
            "MATHJAX",
            # Experimental. Mermaid diagrams: RST raw-html <pre class="mermaid">
            # (all versions, used in 00-04/06) and Markdown ```mermaid fences
            # (strictdoc 0.23.0+, used in 90-appendix-notation.sdoc).
            "MERMAID",
            # Experimental. Requirement x design/test coverage matrix screen.
            # Surfaces which requirements are implemented/verified and their test
            # results across the V-model (Implements/Satisfies/Verifies/ResultOf).
            "TRACEABILITY_MATRIX_SCREEN",
        ],
    )
