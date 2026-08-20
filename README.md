# 🔍 Triagem Automática de Revisão Sistemática (RSL) - Parsifal

Este repositório contém uma ferramenta interativa desenvolvida em **Python** e **Streamlit** para facilitar, acelerar e auditar a etapa de **triagem (screening)** de artigos em Revisões Sistemáticas de Literatura (RSL), a partir de bases exportadas do **Parsifal**, Scopus, IEEE Xplore, PubMed, entre outros.

A ferramenta automatiza a classificação com base em critérios customizáveis de inclusão e exclusão por **Expressões Regulares (Regex)** e gera relatórios e gráficos no padrão **PRISMA 2020**.

---

## 🚀 Como Executar a Aplicação

### 🌐 Acesso Online (Recomendado)
A aplicação está publicada na nuvem e pronta para uso:
👉 **[triagem-parsifal.streamlit.app](https://triagem-parsifal.streamlit.app/)**

---

### 💻 Execução Local (Opcional)
Caso queira executar a ferramenta localmente:
1. **Clone o repositório**:
   ```bash
   git clone https://github.com/nicolasaj0/Triagem-Parsifal.git
   cd Triagem-Parsifal
   ```
2. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Inicie o servidor Streamlit**:
   ```bash
   streamlit run app.py
   ```

4. **Executar Testes Automatizados**:
   ```bash
   pytest tests/ -v
   ```

---

## 🛠️ Funcionalidades Principais

* 📥 **Importação Flexível de Dados**: Suporte a arquivos Excel (`.xlsx`, `.xls`) e arquivos delimitados (`.csv` com separador e codificação detectados automaticamente).
* 🧪 **Testador & Validador de Regex em Tempo Real**: Sandbox interativo para validar a sintaxe e testar expressões regulares contra frases de exemplo antes de aplicar na base.
* ⚙️ **Configuração Dinâmica de Regras**:
  * **Critérios de Exclusão (EX)**: Se a regex for encontrada no texto consolidado, o artigo é automaticamente rejeitado.
  * **Critérios de Inclusão (IN)**: Se a regex não for encontrada, o artigo é rejeitado.
  * **Campos Customizáveis**: Escolha analisar campos específicos por regra (ex: Título, Abstract, Keywords, etc.).
* 🧹 **Tratamento e Limpeza Automática**:
  * Deduplicação inteligente de artigos com normalização de texto.
  * Políticas de identificador **DOI**: remover registros sem DOI, apenas sinalizar no relatório ou ignorar.
* 🔍 **Inspetor e Diagnóstico Individual**: Audite qualquer artigo triado com realce visual dos termos que ativaram os critérios de inclusão/exclusão.
* 📊 **Estatísticas e Diagrama PRISMA 2020**: Gráficos de funil de seleção PRISMA, distribuição de aprovação e impacto por critério de descarte.
* 📦 **Exportação Completa (Multi-Abas)**: Download de uma única planilha Excel `.xlsx` estruturada com abas de **Aprovados**, **Rejeitados** (com motivos detalhados) e **Resumo PRISMA**, além de downloads individuais.
* 💾 **Perfis de Regras**: Exporte ou importe configurações completas de regras em formato `.json`.

---

## 📂 Estrutura do Projeto

* **`app.py`**: Interface web completa e interativa em Streamlit.
* **`triagem_rsl.py`**: Motor central de processamento, deduplicação, regex e geração de relatórios PRISMA.
* **`tests/test_triagem.py`**: Suíte de testes unitários com Pytest.
* **`requirements.txt`**: Dependências do projeto (Streamlit, Pandas, OpenPyXL, Plotly, Pytest).
* **`pytest.ini`**: Configuração de execução de testes.
* **`README.md`**: Manual de instruções da ferramenta.
