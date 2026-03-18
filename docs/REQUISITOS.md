# Requisitos para o Rule34 Downloader

Este script automatiza o download de imagens e vídeos do Rule34 usando a API oficial.

## 1. Dependências do Sistema
*   **Python 3.x**: O script foi desenvolvido para Python 3.
*   **Bibliotecas Necessárias**:
    *   `requests`: Para fazer as requisições HTTP.
    *   `python-dotenv`: Para carregar as credenciais do arquivo `.env`.
    *   `PySide6`: Para a interface gráfica.

> **Instalação:** `pip install -r requirements.txt`

## 2. Arquivos (Opcionais)
*   **`.env`**: Local recomendado para suas credenciais (`R34_API_KEY` e `R34_USER_ID`). O script cria este arquivo se você usar o setup interativo.
*   **`blacklist.txt`**: Se existir, conterá as tags bloqueadas separadas por espaços simples ou linhas. O script as ignora automaticamente em todas as buscas.

## 3. Como Executar
Você pode executar o script de duas formas principais:

### A. Modo Interativo (Simples)
Basta rodar o script e seguir as instruções na tela:
```bash
python3 rule34_downloader.py
```

### B. Modo via Terminal (Rápido)
Passando as tags diretamente como argumentos:
```bash
python3 rule34_downloader.py "cat_ears high_res"
```

### C. Modo Gráfico (GUI)
Para usar a interface de janelas:
```bash
python3 rule34_gui.py
```

## 4. Funcionalidades Principais
*   **Setup Interativo (.env)**: Configuração fácil das credenciais no primeiro uso.
*   **Entrada de Tags Flexível**: Busca automatizada ou manual.
*   **Multithreading**: Baixa múltiplos arquivos simultaneamente para maior velocidade.
*   **Verificação de Duplicatas**: Evita baixar arquivos que já existem na pasta `downloads/`.
*   **Gerenciamento de Blacklist**: Filtro automático de conteúdo indesejado.

## 5. Dicas de Uso
*   **Credenciais:** Para ver seu ID e Chave API, acesse sua conta no Rule34: [Acessar conta](https://rule34.xxx/index.php?page=account&s=options)
*   **Interrupção:** Use `Ctrl+C` no terminal para cancelar o download com segurança a qualquer momento.
