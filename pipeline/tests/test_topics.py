from pipeline.topics import TOPIC_ORDER, normalize_domain, normalize_domains, topics_for


def test_normalize_domain_aliases_and_separators():
    assert normalize_domain(" ML ") == "machine learning"
    assert normalize_domain("NLP") == "natural language processing"
    assert normalize_domain("LLMs") == "large language models"
    assert normalize_domain("Human – Computer Interaction") == "human-computer interaction"
    assert normalize_domains(["ML", "machine learning", "", "FPGAs"]) == [
        "machine learning",
        "fpga",
    ]


def test_topics_word_start_matching():
    assert topics_for(["artificial intelligence"]) == ["Machine learning & AI"]
    assert "Humanities & society" not in topics_for(["artificial intelligence"])
    assert topics_for(["art history"]) == ["Humanities & society"]
    assert "Environment & civil engineering" not in topics_for(["geometry processing"])
    assert topics_for(["fpga", "risc-v"]) == ["Hardware & circuits"]
    assert "Security & privacy" in topics_for(["trusted execution"])
    assert topics_for(["rust ownership"]) == ["Programming languages & verification"]
    assert topics_for(["trust"]) == ["Security & privacy"]  # "trust" is not the language Rust


def test_topics_multiple_in_display_order():
    got = topics_for(["deep learning", "biomedical signal processing"])
    assert got == [
        "Machine learning & AI",
        "Signal processing & acoustics",
        "Health & life sciences",
    ]
    assert got == sorted(got, key=TOPIC_ORDER.index)
