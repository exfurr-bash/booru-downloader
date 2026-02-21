# 🔞 Rule34 Downloader - O Aspirador de Pixels 🚀

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-ready_for_culture-orange.svg)

Bem-vindo ao **Rule34 Downloader**, a ferramenta definitiva para quem não tem tempo a perder clicando em "Próxima Página" enquanto tenta... eh... "estudar anatomia digital". 🧐

Este script automatiza a busca e o download de conteúdos do Rule34, garantindo que sua coleção local cresça mais rápido do que a sua lista de arrependimentos.

---

## ✨ Funcionalidades (O que essa belezura faz?)

*   **⚡ Turbo Download:** Usa multithreading (10 conexões simultâneas) para baixar tudo na velocidade da luz.
*   **🛡️ Escudo Anti-Trauma (Blacklist):** Integração automática com sua lista de tags proibidas. Mantenha sua sanidade intacta!
*   **🤖 Setup Inteligente:** Nunca usou um script? Sem problemas. O modo interativo te guia pela configuração da API.
*   **📂 Organização Automática:** Cria a pasta `downloads/` e evita baixar arquivos duplicados. Economia de disco é vida!
*   **🕶️ Modo CLI e Interativo:** Use como um hacker no terminal ou responda às perguntas do script como um cavalheiro.

---

## 🛠️ Instalação (Rápido e sem dor)

1.  **Tenha o Python 3 instalado.**
2.  **Instale as dependências necessárias:**
    ```bash
    pip install requests python-dotenv
    ```
3.  **Clone este repositório.**

---

## 🚀 Como Usar (Escolha seu estilo)

### A. O Executivo (Modo Interativo) 👔
Apenas execute o script e deixe que ele pergunte o que você deseja:
```bash
python3 rule34_downloader.py
```
*Dica: Na primeira vez, ele vai te ajudar a configurar seu `.env` com sua API Key.*

### B. O Hacker de Cinema (Modo Terminal) 💻
Passe as tags diretamente e veja a mágica acontecer:
```bash
python3 rule34_downloader.py "cat_ears high_res"
```

---

## 📋 Configuração (O Coração da Máquina)

### 🔑 Credenciais API (.env)
O script agora usa o arquivo `.env` para organizar suas credenciais. O script pode criar isso para você, mas se preferir fazer na mão:
Crie um arquivo `.env` na raiz do projeto:
```env
R34_API_KEY=sua_chave_aqui
R34_USER_ID=seu_id_aqui
```
*Observação: O arquivo `api.txt` ainda é suportado para migração, mas o `.env` é o novo padrão.*

### 🚫 Blacklist
Adicione as tags que você **NUNCA** quer ver no arquivo `disgustingthings-aka-blacklist.txt`, separadas por espaços. O script vai automaticamente dizer "Nem pensar!" para essas tags na API.

---

## ⚠️ Aviso Legal (O famoso "Eu não vi nada")

Este script é uma ferramenta de automação. O autor não se responsabiliza pelo que você decide baixar, pela sua saúde mental após buscas duvidosas, ou pelo que sua mãe vai dizer se encontrar sua pasta `downloads/`. Use com responsabilidade (e talvez no modo anônimo). 🕵️‍♂️

---

## 🤝 Contribuições

Achou um bug? Quer adicionar uma funcionalidade de "Auto-Ocultar quando o chefe passar"? Sinta-se à vontade para abrir um Pull Request!

---

**Feito com ❤️ (e muita cafeína) por quem entende de... automação.**
