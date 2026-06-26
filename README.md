# SecureDoc2MD

Converta arquivos PDF, DOCX e XLSX para Markdown de forma segura através de uma interface web.
Obs: o resultado pode conter erros. Revise e, se for necessário, edite para correção.

## Início Rápido - Docker (melhor opção)

```bash
docker build -t securedoc2md .
docker run --rm -it -p 8501:8501 securedoc2md

```

Abra http://localhost:8501 no seu navegador.

## Desenvolvimento Local

### Pré-requisitos

* Python 3.14+
* Biblioteca do sistema: `libmagic` (Ubuntu/Debian: `apt install libmagic1`, macOS: `brew install libmagic`)

### Configuração

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

### Executar

```bash
python run.py

```

## Estrutura do Projeto

```
secure_doc2md/
├── src/
│   ├── security.py      # Validação de MIME, sanitização de nome de arquivo, segurança de caminho (path safety)
│   ├── converter.py      # Wrapper do MarkItDown com execução em diretório temporário isolado
│   └── web.py            # Interface web em Streamlit
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── run.py                # Ponto de entrada com cabeçalhos de segurança

```

## Segurança

Todos os arquivos enviados são validados pelo seu tipo MIME real (magic bytes), e não pela extensão do arquivo. Arquivos que excedem 50 MB são rejeitados. Os arquivos temporários são criados em um diretório isolado e destruídos imediatamente após a conversão. O limite de taxa (rate limiting de 10 requisições por 60 segundos por IP) previne abusos. O container Docker é executado como um usuário não-root.

## Formatos Suportados

| Formato | Tipo MIME |
| --- | --- |
| PDF | application/pdf |
| DOCX | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| XLSX | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `LOG_LEVEL` | `DEBUG` | Nível de log do Python (DEBUG, INFO, WARNING, ERROR) |
