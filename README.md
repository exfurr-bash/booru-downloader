# NEW EXTREMELY BIG UPDATE SOON
# Booru Downloader - CLI e GUI Tool 🚀

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-ready-orange.svg)

Booru Downloader é uma ferramenta Python que automatiza o download de imagens de APIs compatíveis com Danbooru. Suporta CLI e interface gráfica (GUI), multithreading e gerenciamento de blacklist.

---

## Estrutura do Projeto

* **Turbo Download:** Multithreading com threads configuráveis para acelerar downloads.
* **GUI Moderna:** Interface com múltiplos temas (Cyberpunk, Retro Hacker, etc.) e redimensionamento dinâmico.
* **Autocomplete Assíncrono:** Sugestões de tags em tempo real sem travar a interface.
* **Blacklist:** Bloqueio de tags indesejadas via arquivo de configuração (`blacklist.txt`).
* **Setup Automatizado:** Configuração inicial guiada para credenciais da API via `.env`.
* **Organização Automática:** Cria e gerencia a pasta `downloads/`, evitando arquivos duplicados.
* **CLI e GUI:** Escolha entre linha de comando ou interface gráfica para interação.
*   `rule34_downloader.py`: Script principal para terminal (CLI).
*   `rule34_gui.py`: Script principal para interface gráfica (GUI).
*   `core/`: Motor de download (engine) do projeto.
*   `docs/`: Requisitos, notas de melhorias e referências da API.
*   `tests/`: Testes unitários para garantir o funcionamento do motor.
*   `blacklist.txt`: Sua lista pessoal de tags bloqueadas.
*   `requirements.txt`: Dependências necessárias para o projeto.


---

## Instalação

1. Tenha Python 3 instalado.
2. Clone o repositório:

```bash
git clone https://github.com/exfurr-bash/booru-downloader.git
cd booru-downloader
```

3. Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

4. Instale as dependências dentro do ambiente virtual:

```bash
pip install -r requirements.txt
# ou
pip install requests python-dotenv PySide6
```

---

## Uso

### CLI

Modo terminal direto:

```bash
python3 rule34_downloader.py "tag1 tag2"
```

Modo interativo:

```bash
python3 rule34_downloader.py
```

---

### GUI

Roda a interface gráfica:

```bash
python3 rule34_gui.py
```

---

## Configuração

### Credenciais API (.env)

Crie um arquivo `.env` na raiz do projeto:

```env
R34_API_KEY=sua_chave_aqui
R34_USER_ID=seu_id_aqui
```

O script também suporta migração do arquivo antigo `api.txt`.

### Blacklist

Adicione tags que **não devem ser baixadas** no arquivo:

```
blacklist.txt
```

---


###  Dicas de Uso
- Para ver seu ID e Chave API, acesse: [Acessar conta Rule34](https://rule34.xxx/index.php?page=account&s=options)
---


## Aviso Legal

Use esta ferramenta de acordo com os termos de serviço do site alvo. O autor não se responsabiliza pelo uso indevido da ferramenta.

---

## Contribuições

Bugs, melhorias ou novas funcionalidades podem ser adicionadas via Pull Request.
