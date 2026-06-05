from knowledge_agent.vector_index import LocalVectorIndex, embed_text


def test_embed_text_places_related_terms_near_each_other():
    query = embed_text("neural retrieval")
    related = embed_text("retrieval augmented generation")
    unrelated = embed_text("green tea protocol")

    assert query.similarity(related) > query.similarity(unrelated)


def test_local_vector_index_persists_entries(tmp_path):
    index_path = tmp_path / "library" / "indexes" / "vectors" / "chunks.json"
    index = LocalVectorIndex(index_path)
    index.replace_document_entries(
        document_id=10,
        entries=[
            (1, "neural retrieval systems"),
            (2, "green tea protocol"),
        ],
    )

    reloaded = LocalVectorIndex(index_path)

    assert reloaded.search("retrieval", limit=1)[0].chunk_id == 1
    assert index_path.exists()
