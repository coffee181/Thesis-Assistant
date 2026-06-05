from knowledge_agent.bibliography import (
    export_bibtex,
    export_ris,
    parse_bibtex,
    parse_ris,
)
from knowledge_agent.models import Paper


def test_parse_bibtex_records_metadata_fields():
    records = parse_bibtex(
        """
        @article{doe2024local,
          title = {Local Knowledge Agents},
          author = {Jane Doe and John Smith},
          year = {2024},
          doi = {10.1234/LOCAL.2024},
          journal = {Journal of Local Research},
          abstract = {A study of traceable local research assistants.},
          eprint = {2401.12345}
        }
        """
    )

    assert len(records) == 1
    record = records[0]
    assert record.citation_key == "doe2024local"
    assert record.title == "Local Knowledge Agents"
    assert record.authors == "Jane Doe and John Smith"
    assert record.year == 2024
    assert record.doi == "10.1234/LOCAL.2024"
    assert record.venue == "Journal of Local Research"
    assert record.abstract == "A study of traceable local research assistants."
    assert record.arxiv_id == "2401.12345"
    assert record.entry_type == "article"


def test_parse_ris_records_metadata_fields():
    records = parse_ris(
        """
        TY  - JOUR
        ID  - doe2024local
        TI  - Local Knowledge Agents
        AU  - Jane Doe
        AU  - John Smith
        PY  - 2024
        DO  - 10.1234/LOCAL.2024
        JO  - Journal of Local Research
        AB  - A study of traceable local research assistants.
        ER  -
        """
    )

    assert len(records) == 1
    record = records[0]
    assert record.citation_key == "doe2024local"
    assert record.title == "Local Knowledge Agents"
    assert record.authors == "Jane Doe and John Smith"
    assert record.year == 2024
    assert record.doi == "10.1234/LOCAL.2024"
    assert record.venue == "Journal of Local Research"
    assert record.abstract == "A study of traceable local research assistants."
    assert record.entry_type == "jour"


def test_export_bibtex_uses_stable_keys_and_escapes_fields():
    content = export_bibtex(
        [
            Paper(
                id=1,
                title="Local {Knowledge} Agents",
                authors="Jane Doe and John Smith",
                year=2024,
                doi="10.1234/local",
                venue="Journal of Local Research",
                abstract="Uses {grounded} answers.",
                citation_key=None,
                arxiv_id="2401.12345",
                entry_type="article",
                created_at="2026-06-05T00:00:00",
            )
        ]
    )

    assert "@article{doe2024local," in content
    assert "title = {Local \\{Knowledge\\} Agents}" in content
    assert "author = {Jane Doe and John Smith}" in content
    assert "year = {2024}" in content
    assert "doi = {10.1234/local}" in content
    assert "journal = {Journal of Local Research}" in content
    assert "abstract = {Uses \\{grounded\\} answers.}" in content
    assert "eprint = {2401.12345}" in content


def test_export_ris_includes_expected_tags():
    content = export_ris(
        [
            Paper(
                id=1,
                title="Local Knowledge Agents",
                authors="Jane Doe and John Smith",
                year=2024,
                doi="10.1234/local",
                venue="Journal of Local Research",
                abstract="Uses grounded answers.",
                citation_key="doe2024local",
                arxiv_id=None,
                entry_type="article",
                created_at="2026-06-05T00:00:00",
            )
        ]
    )

    assert "TY  - JOUR" in content
    assert "ID  - doe2024local" in content
    assert "TI  - Local Knowledge Agents" in content
    assert "AU  - Jane Doe" in content
    assert "AU  - John Smith" in content
    assert "PY  - 2024" in content
    assert "DO  - 10.1234/local" in content
    assert "JO  - Journal of Local Research" in content
    assert "AB  - Uses grounded answers." in content
    assert content.strip().endswith("ER  -")
