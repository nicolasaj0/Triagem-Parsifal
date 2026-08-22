# Triagem Automática de Revisão Sistemática (RSL) - Parsifal

Ferramenta interativa em Python e Streamlit para acelerar e auditar a etapa de triagem de artigos em Revisões Sistemáticas de Literatura (RSL), a partir de bases exportadas do Parsifal, Scopus, IEEE Xplore, PubMed, entre outras.

A classificação é feita com base em critérios de inclusão e exclusão definidos por expressões regulares (regex), com geração de relatórios e gráficos no padrão PRISMA 2020.

## Como executar

### Acesso online

A aplicação está publicada em: [triagem-parsifal.streamlit.app](https://triagem-parsifal.streamlit.app/)

### Execução local

```bash
git clone https://github.com/nicolasaj0/Triagem-Parsifal.git
cd Triagem-Parsifal
pip install -r requirements.txt
streamlit run app.py
```

Para rodar os testes automatizados:

```bash
pytest tests/ -v
```

## Funcionalidades

- **Importação de dados**: arquivos Excel (`.xlsx`, `.xls`) e arquivos delimitados (`.csv`), com detecção automática de separador e codificação.
- **Testador de regex em tempo real**: sandbox para validar sintaxe e testar expressões regulares contra frases de exemplo antes de aplicar na base.
- **Configuração de regras**:
  - Critérios de exclusão (EX): se a regex for encontrada no texto consolidado, o artigo é rejeitado.
  - Critérios de inclusão (IN): se a regex não for encontrada, o artigo é rejeitado.
  - Campos customizáveis por regra (título, abstract, keywords etc.).
- **Limpeza de dados**:
  - Deduplicação de artigos com normalização de texto.
  - Políticas de identificador DOI: remover registros sem DOI, apenas sinalizar no relatório ou ignorar.
- **Inspetor individual**: auditoria de qualquer artigo triado, com realce dos termos que ativaram os critérios de inclusão/exclusão.
- **Estatísticas e diagrama PRISMA 2020**: funil de seleção, distribuição de aprovação e impacto por critério de descarte.
- **Exportação**: planilha Excel única com abas de Aprovados, Rejeitados (com motivos detalhados) e Resumo PRISMA, além de downloads individuais.
- **Perfis de regras**: exportação e importação de configurações de regras em formato `.json`.

## Estrutura do projeto

- `app.py` — interface web em Streamlit.
- `triagem_rsl.py` — motor de processamento: deduplicação, regex e geração de relatórios PRISMA.
- `tests/test_triagem.py` — suíte de testes unitários com Pytest.
- `requirements.txt` — dependências do projeto (Streamlit, Pandas, OpenPyXL, Plotly, Pytest).
- `pytest.ini` — configuração de execução de testes.
- `README.md` — este arquivo.
