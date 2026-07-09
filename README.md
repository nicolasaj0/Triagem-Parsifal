# 🔍 Triagem Automática de Revisão Sistemática (RSL) - Parsifal

Este repositório contém uma ferramenta interativa desenvolvida em **Python** e **Streamlit** para facilitar e acelerar a etapa de **triagem (screening)** de artigos em Revisões Sistemáticas de Literatura (RSL), a partir de planilhas exportadas do **Parsifal**.

A ferramenta permite analisar de forma automatizada e flexível os elementos textuais (título, abstract, keywords) dos artigos com base em regras customizáveis de inclusão e exclusão.

---

## 🚀 Como Executar a Aplicação

### 🌐 Acesso Online (Recomendado)
A aplicação está publicada na nuvem e pronta para uso! Acesse diretamente pelo link:
👉 **[triagem-parsifal.streamlit.app](https://triagem-parsifal.streamlit.app/)**

---

### 💻 Execução Local (Opcional)
Caso queira executar a ferramenta localmente na sua máquina:
1. **Clone o repositório** ou faça o download dos arquivos:
   ```bash
   git clone https://github.com/nicolasaj0/Triagem-Parsifal.git
   cd Triagem-Parsifal
   ```
2. **Instale as dependências** necessárias:
   ```bash
   pip install -r requirements.txt
   ```
3. **Inicie o servidor local** do Streamlit:
   ```bash
   streamlit run app.py
   ```
4. A aplicação abrirá automaticamente no endereço: `http://localhost:8501`.

---

## 🛠️ Funcionalidades Principais

* 📥 **Upload de Planilha**: Carregue o arquivo Excel nos formatos `.xlsx` ou `.xls` gerados pelo Parsifal contendo os artigos não classificados.
* ⚙️ **Configuração Dinâmica de Regras**:
  * **Critérios de Exclusão (EX)**: Se a expressão regular for encontrada no texto consolidado, o artigo é automaticamente rejeitado.
  * **Critérios de Inclusão (IN)**: Se a expressão regular não for encontrada, o artigo é rejeitado.
  * Selecione quais colunas específicas da planilha analisar para cada regra individual (ex: apenas no Título, ou no Abstract + Keywords).
* ⚙️ **Limpeza Geral Personalizada**:
  * Ative/Desative a detecção automática de artigos duplicados (com base na coluna do título normalizado).
  * Defina a estratégia para artigos sem identificador **DOI**: remover automaticamente, apenas sinalizar no relatório final (mantendo o artigo) ou ignorar o filtro.
* 💾 **Perfil de Regras**: Salve toda a sua configuração personalizada de filtros exportando para um arquivo `.json` e importe de volta quando desejar para carregar o mesmo conjunto de regras.
* 📊 **Gráficos e Estatísticas**: Acompanhe o percentual de aceitação e os motivos mais frequentes de descarte com gráficos visuais em tempo real.
* 📤 **Exportação Facilitada**: Faça o download das planilhas resultantes de artigos **Aprovados** e **Rejeitados** (com os respectivos motivos detalhados) formatadas em `.xlsx`.

---

## 📂 Estrutura de Arquivos Recomendada para Subir ao GitHub

Para manter seu repositório organizado e focado apenas na ferramenta, suba os seguintes arquivos:
* **`app.py`**: Código-fonte da interface visual e da estrutura web em Streamlit.
* **`triagem_rsl.py`**: Script contendo a lógica centralizada de filtragem e classificação de artigos.
* **`requirements.txt`**: Definição das bibliotecas necessárias (Streamlit, Pandas e OpenPyXL).
* **`README.md`**: Este manual de instruções da ferramenta.
* **`.gitignore`**: Arquivo para evitar que planilhas de dados locais (`.xlsx`) ou arquivos temporários de cache sejam enviados acidentalmente ao GitHub.
