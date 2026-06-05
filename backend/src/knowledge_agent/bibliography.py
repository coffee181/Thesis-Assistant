import re

from knowledge_agent.models import BibliographyRecord, Paper


def parse_bibtex(content: str) -> list[BibliographyRecord]:
    records: list[BibliographyRecord] = []
    for entry_type, body in _iter_bibtex_entries(content):
        citation_key, fields = _parse_bibtex_body(body)
        title = _clean_text(fields.get("title") or citation_key or "Untitled")
        authors = _clean_text(fields.get("author"))
        records.append(
            BibliographyRecord(
                citation_key=_clean_text(citation_key),
                title=title,
                authors=authors,
                year=_parse_year(fields.get("year") or fields.get("date")),
                doi=_clean_text(fields.get("doi")),
                venue=_clean_text(
                    fields.get("journal")
                    or fields.get("journaltitle")
                    or fields.get("booktitle")
                    or fields.get("venue")
                ),
                abstract=_clean_text(fields.get("abstract")),
                arxiv_id=_clean_text(
                    fields.get("eprint") or fields.get("arxiv") or fields.get("arxivid")
                ),
                entry_type=entry_type.lower(),
            )
        )
    return records


def parse_ris(content: str) -> list[BibliographyRecord]:
    records: list[BibliographyRecord] = []
    current: dict[str, list[str]] | None = None
    last_tag: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        match = re.match(r"^([A-Z0-9]{2})\s+-\s?(.*)$", line.strip())
        if match is None:
            if current is not None and last_tag is not None and line.strip():
                current[last_tag][-1] = f"{current[last_tag][-1]} {line.strip()}"
            continue

        tag = match.group(1)
        value = match.group(2).strip()
        if tag == "TY":
            current = {"TY": [value]}
            last_tag = tag
            continue
        if current is None:
            continue
        if tag == "ER":
            records.append(_ris_record_from_tags(current))
            current = None
            last_tag = None
            continue
        current.setdefault(tag, []).append(value)
        last_tag = tag

    if current is not None:
        records.append(_ris_record_from_tags(current))

    return records


def parse_bibliography(content: str, format_name: str) -> list[BibliographyRecord]:
    normalized = format_name.strip().lower()
    if normalized in {"bib", "bibtex"}:
        return parse_bibtex(content)
    if normalized == "ris":
        return parse_ris(content)
    raise ValueError(f"unsupported bibliography format: {format_name}")


def export_bibtex(papers: list[Paper]) -> str:
    entries: list[str] = []
    for paper in papers:
        entry_type = (paper.entry_type or "article").lower()
        citation_key = paper.citation_key or _stable_citation_key(paper)
        fields = [
            ("title", paper.title),
            ("author", paper.authors),
            ("year", str(paper.year) if paper.year is not None else None),
            ("doi", paper.doi),
            (_bibtex_venue_field(entry_type), paper.venue),
            ("abstract", paper.abstract),
            ("eprint", paper.arxiv_id),
        ]
        rendered_fields = [
            f"  {name} = {{{_escape_bibtex_value(value)}}}"
            for name, value in fields
            if value
        ]
        entries.append(f"@{entry_type}{{{citation_key},\n" + ",\n".join(rendered_fields) + "\n}")
    return "\n\n".join(entries)


def export_ris(papers: list[Paper]) -> str:
    records: list[str] = []
    for paper in papers:
        lines = [f"TY  - {_ris_type(paper.entry_type)}"]
        lines.append(f"ID  - {paper.citation_key or _stable_citation_key(paper)}")
        lines.append(f"TI  - {paper.title}")
        for author in _split_authors(paper.authors):
            lines.append(f"AU  - {author}")
        if paper.year is not None:
            lines.append(f"PY  - {paper.year}")
        if paper.doi:
            lines.append(f"DO  - {paper.doi}")
        if paper.venue:
            lines.append(f"JO  - {paper.venue}")
        if paper.abstract:
            lines.append(f"AB  - {paper.abstract}")
        lines.append("ER  -")
        records.append("\n".join(lines))
    return "\n\n".join(records)


def _iter_bibtex_entries(content: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    position = 0
    while position < len(content):
        at_index = content.find("@", position)
        if at_index == -1:
            break
        type_match = re.match(r"@([A-Za-z]+)\s*([\{\(])", content[at_index:])
        if type_match is None:
            position = at_index + 1
            continue

        entry_type = type_match.group(1)
        open_char = type_match.group(2)
        close_char = "}" if open_char == "{" else ")"
        body_start = at_index + type_match.end()
        body_end = _find_matching_delimiter(content, body_start - 1, open_char, close_char)
        if body_end == -1:
            break
        entries.append((entry_type, content[body_start:body_end]))
        position = body_end + 1
    return entries


def _find_matching_delimiter(
    content: str,
    open_index: int,
    open_char: str,
    close_char: str,
) -> int:
    depth = 0
    in_quote = False
    escaped = False
    for index in range(open_index, len(content)):
        char = content[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and not escaped:
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _parse_bibtex_body(body: str) -> tuple[str | None, dict[str, str]]:
    key, remainder = _split_top_level_once(body, ",")
    fields: dict[str, str] = {}
    position = 0
    while position < len(remainder):
        while position < len(remainder) and remainder[position] in " \t\r\n,":
            position += 1
        name_match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", remainder[position:])
        if name_match is None:
            break
        name = name_match.group(1).lower()
        position += name_match.end()
        value, position = _read_bibtex_value(remainder, position)
        fields[name] = value
        while position < len(remainder) and remainder[position] != ",":
            position += 1
        if position < len(remainder) and remainder[position] == ",":
            position += 1
    return key.strip() or None, fields


def _split_top_level_once(value: str, delimiter: str) -> tuple[str, str]:
    depth = 0
    in_quote = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char in "{(":
            depth += 1
        elif char in "})":
            depth -= 1
        elif char == delimiter and depth == 0:
            return value[:index], value[index + 1 :]
    return value, ""


def _read_bibtex_value(source: str, position: int) -> tuple[str, int]:
    while position < len(source) and source[position].isspace():
        position += 1
    if position >= len(source):
        return "", position

    if source[position] == "{":
        end = _find_matching_delimiter(source, position, "{", "}")
        if end == -1:
            return source[position + 1 :], len(source)
        return source[position + 1 : end], end + 1

    if source[position] == '"':
        index = position + 1
        escaped = False
        while index < len(source):
            char = source[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                return source[position + 1 : index], index + 1
            index += 1
        return source[position + 1 :], len(source)

    index = position
    while index < len(source) and source[index] != ",":
        index += 1
    return source[position:index].strip(), index


def _ris_record_from_tags(tags: dict[str, list[str]]) -> BibliographyRecord:
    title = _first(tags, "TI", "T1") or _first(tags, "ID") or "Untitled"
    authors = " and ".join(tags.get("AU", [])) or None
    return BibliographyRecord(
        citation_key=_first(tags, "ID"),
        title=title,
        authors=authors,
        year=_parse_year(_first(tags, "PY", "Y1", "DA")),
        doi=_first(tags, "DO"),
        venue=_first(tags, "JO", "JF", "T2"),
        abstract=_first(tags, "AB"),
        arxiv_id=None,
        entry_type=(_first(tags, "TY") or "").lower() or None,
    )


def _first(tags: dict[str, list[str]], *names: str) -> str | None:
    for name in names:
        for value in tags.get(name, []):
            cleaned = _clean_text(value)
            if cleaned:
                return cleaned
    return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("\\{", "{").replace("\\}", "}")
    cleaned = re.sub(r"[{}]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d{4}", value)
    return int(match.group(0)) if match else None


def _bibtex_venue_field(entry_type: str) -> str:
    if entry_type in {"inproceedings", "conference", "proceedings"}:
        return "booktitle"
    return "journal"


def _ris_type(entry_type: str | None) -> str:
    normalized = (entry_type or "").lower()
    if normalized in {"inproceedings", "conference", "proceedings", "conf"}:
        return "CONF"
    if normalized in {"book", "chapter"}:
        return "BOOK"
    return "JOUR"


def _split_authors(authors: str | None) -> list[str]:
    if not authors:
        return []
    return [author.strip() for author in authors.split(" and ") if author.strip()]


def _stable_citation_key(paper: Paper) -> str:
    first_author = _split_authors(paper.authors)[0] if paper.authors else ""
    author_token = re.sub(r"[^a-z0-9]+", "", first_author.split()[-1].lower())
    title_words = re.findall(r"[A-Za-z0-9]+", paper.title.lower())
    title_token = title_words[0] if title_words else ""
    year_token = str(paper.year) if paper.year is not None else "nodate"
    key = f"{author_token}{year_token}{title_token}"
    return key or f"paper{paper.id}"


def _escape_bibtex_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
