"""Keep both published rendition migration histories deployable after branch sync."""

from django.db.migrations.loader import MigrationLoader


def test_rendicion_release_has_one_leaf_covering_both_published_histories():
    loader = MigrationLoader(None)
    conflicts = loader.detect_conflicts()
    assert "rendicioncuentasmensual" not in conflicts, conflicts
    leaves = loader.graph.leaf_nodes("rendicioncuentasmensual")
    assert len(leaves) == 1
    plan = loader.graph.forwards_plan(leaves[0])
    assert (
        "rendicioncuentasmensual",
        "0027_issue_2845_pdf_descarga",
    ) in plan
    assert (
        "rendicioncuentasmensual",
        "0028_upload_to_nombre_acotado",
    ) in plan
    merge = loader.disk_migrations[
        ("rendicioncuentasmensual", "0029_merge_pdf_descarga_upload_to")
    ]
    assert merge.operations == []
