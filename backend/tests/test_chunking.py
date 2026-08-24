from app.services.chunking import chunk_text


def test_empty_text_produces_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_is_a_single_chunk():
    text = "one two three four five"
    chunks = chunk_text(text)
    assert chunks == [text]


def test_long_text_is_split_into_multiple_overlapping_chunks():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size_tokens=500, overlap_tokens=50)

    assert len(chunks) > 1
    # every word must appear in at least one chunk (no gaps)
    covered = set()
    for chunk in chunks:
        covered.update(chunk.split())
    assert covered == set(words)


def test_overlap_boundary_shares_words_between_consecutive_chunks():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size_tokens=500, overlap_tokens=50)

    first_words = chunks[0].split()
    second_words = chunks[1].split()
    overlap = set(first_words) & set(second_words)
    assert len(overlap) > 0


def test_last_chunk_reaches_the_end_of_the_text():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size_tokens=500, overlap_tokens=50)

    assert chunks[-1].split()[-1] == words[-1]
