import pytest
import pandas as pd
import io
import os
from triagem_rsl import (
    executar_triagem,
    carregar_base_artigos,
    gerar_excel_multi_abas,
    DEFAULT_RULES
)

@pytest.fixture
def sample_dataframe():
    data = [
        {
            "bibtex_key": "art1",
            "title": "Procedural Dungeon Generation with BSP Trees",
            "author": "Silva, J.",
            "journal": "Game Studies",
            "year": 2022,
            "abstract": "We present an approach for generating game dungeons procedurally using binary space partitioning.",
            "doi": "10.1000/182",
            "keywords": "pcg; dungeon generation; bsp"
        },
        {
            "bibtex_key": "art2",
            "title": "A Systematic Review on Procedural Content Generation in Games",
            "author": "Santos, M.",
            "journal": "IEEE Transactions on Games",
            "year": 2021,
            "abstract": "This survey paper investigates recent trends in procedural content generation for video games.",
            "doi": "10.1000/183",
            "keywords": "review; survey; procedural content generation"
        },
        {
            "bibtex_key": "art3",
            "title": "  procedural dungeon generation with bsp trees  ",
            "author": "Silva, J. Duplicate",
            "journal": "Game Studies",
            "year": 2022,
            "abstract": "Duplicate abstract.",
            "doi": "10.1000/182",
            "keywords": "pcg"
        },
        {
            "bibtex_key": "art4",
            "title": "Procedural Map Generation without DOI",
            "author": "Lima, R.",
            "journal": "Indie Games Journal",
            "year": 2020,
            "abstract": "We explore procedural level generation techniques.",
            "doi": "",
            "keywords": "pcg; levels"
        },
        {
            "bibtex_key": "art5",
            "title": "Machine Learning for Natural Language Processing",
            "author": "Souza, F.",
            "journal": "AI Journal",
            "year": 2023,
            "abstract": "A study on deep learning transformers for NLP text generation.",
            "doi": "10.1000/185",
            "keywords": "nlp; transformers"
        }
    ]
    return pd.DataFrame(data)


def test_deduplicacao(sample_dataframe):
    rules = DEFAULT_RULES
    res = executar_triagem(
        df=sample_dataframe,
        rules=rules,
        remover_duplicatas=True,
        coluna_dedup="title",
        estrategia_doi="ignore"
    )
    stats = res["stats"]
    assert stats["total_inicial"] == 5
    assert stats["duplicatas_removidas"] == 1
    assert stats["pos_limpeza"] == 4


def test_estrategias_doi(sample_dataframe):
    # Teste REMOVE
    res_remove = executar_triagem(
        df=sample_dataframe,
        rules=DEFAULT_RULES,
        remover_duplicatas=False,
        estrategia_doi="remove"
    )
    assert res_remove["stats"]["sem_doi"] == 1
    assert res_remove["stats"]["pos_limpeza"] == 4

    # Teste FLAG
    res_flag = executar_triagem(
        df=sample_dataframe,
        rules=DEFAULT_RULES,
        remover_duplicatas=False,
        estrategia_doi="flag"
    )
    assert res_flag["stats"]["sem_doi"] == 0
    assert res_flag["stats"]["sem_doi_flagged"] == 1
    assert "sem_doi_alerta" in res_flag["aprovados"].columns or "sem_doi_alerta" in res_flag["rejeitados"].columns


def test_classificacao_regras(sample_dataframe):
    res = executar_triagem(
        df=sample_dataframe,
        rules=DEFAULT_RULES,
        remover_duplicatas=True,
        estrategia_doi="remove"
    )
    aprovados = res["aprovados"]
    rejeitados = res["rejeitados"]
    stats = res["stats"]

    # art1 deve ser aprovado (tem 'procedural' e não tem termos de 'review')
    # art2 deve ser rejeitado por EX1 (review/survey)
    # art3 é duplicata de art1 (removido antes)
    # art4 não tem DOI (removido antes)
    # art5 não tem 'procedural' (rejeitado por falta de IN1)
    
    assert len(aprovados) == 1
    assert aprovados.iloc[0]["title"] == "Procedural Dungeon Generation with BSP Trees"

    assert len(rejeitados) == 2
    motivos_art2 = rejeitados[rejeitados["title"].str.contains("Systematic Review")]["motivo_rejeicao"].values[0]
    assert "EX1" in motivos_art2

    motivos_art5 = rejeitados[rejeitados["title"].str.contains("Natural Language")]["motivo_rejeicao"].values[0]
    assert "Falta IN1" in motivos_art5


def test_case_insensitive_regex(sample_dataframe):
    rules = [
        {
            "id": "IN_UPPER",
            "name": "PCG em Maiúsculas",
            "type": "inclusion",
            "pattern": r"PCG",
            "fields": ["keywords"]
        }
    ]
    res = executar_triagem(sample_dataframe, rules, remover_duplicatas=False, estrategia_doi="ignore")
    # Deve dar match em 'pcg' mesmo que a regex seja 'PCG'
    stats = res["stats"]
    assert stats["regra_stats"]["IN_UPPER"] == 2  # art2 e art5 não têm 'pcg' em keywords


def test_regex_invalida_resiliencia(sample_dataframe):
    rules_com_erro = [
        {
            "id": "EX_INVALIDA",
            "name": "Regex Quebrada",
            "type": "exclusion",
            "pattern": r"[a-z(invalid",
            "fields": ["title"]
        }
    ]
    # Não deve lançar exceção
    res = executar_triagem(sample_dataframe, rules_com_erro, remover_duplicatas=False, estrategia_doi="ignore")
    assert res["stats"]["pos_limpeza"] == 5


def test_carregar_base_artigos_csv(tmp_path):
    csv_file = tmp_path / "teste_artigos.csv"
    csv_file.write_text("title;author;doi\nArtigo Teste;Autor 1;10.123/456", encoding="utf-8")
    
    df = carregar_base_artigos(str(csv_file))
    assert "title" in df.columns
    assert len(df) == 1
    assert df.iloc[0]["author"] == "Autor 1"


def test_gerar_excel_multi_abas(sample_dataframe):
    res = executar_triagem(sample_dataframe, DEFAULT_RULES)
    excel_bytes = gerar_excel_multi_abas(res["aprovados"], res["rejeitados"], res["stats"], DEFAULT_RULES)
    
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0
    
    # Validar que o Excel pode ser lido com as 3 abas esperadas
    excel_io = io.BytesIO(excel_bytes)
    xl = pd.ExcelFile(excel_io)
    assert "Artigos_Aprovados" in xl.sheet_names
    assert "Artigos_Rejeitados" in xl.sheet_names
    assert "Resumo_PRISMA" in xl.sheet_names
