# Clipping digital automatizado — UFSB / ACS

Processa automaticamente o histórico da planilha de clipping da ACS
(alimentada desde 2021): lê cada notícia registrada em **"List of All
Alerts"**, verifica se é sobre a UFSB, calcula sentimento e categoria, e
lança as relevantes em **"clipping tratado"** — na ordem cronológica em
que aconteceram. Roda sozinho, 3 vezes por dia, de graça, via GitHub
Actions.

## Como funciona, resumidamente

- **Fonte**: aba "List of All Alerts" (mecanismo antigo, tipo IFTTT —
  continua alimentando essa aba do jeito que já faz hoje; o pipeline só lê).
- **Como sabe se é sobre a UFSB**: como essa aba só tem Data/Veículo/URL
  (sem título), o pipeline abre cada link e lê o conteúdo da página.
- **Destino**: aba "clipping tratado", só as notícias relevantes, com
  sentimento e categoria já preenchidos. A coluna "viés" (curadoria
  manual) nunca é tocada.
- **Controle de progresso**: uma coluna nova, "Status do processamento",
  é adicionada em "List of All Alerts" para marcar o que já foi visto —
  assim, cada execução só olha o que ainda está pendente.
- **Aviso importante sobre o histórico**: são ~4 anos de notícias
  acumuladas. O pipeline processa até 300 pendentes por execução
  (ajustável em `config.py`), da mais antiga para a mais nova, para não
  estourar o tempo do GitHub Actions. Com 3 execuções por dia, o
  histórico vai sendo varrido aos poucos — pode levar alguns dias até
  zerar a fila, dependendo de quantas notícias existem acumuladas.
  Espere também bastante "Erro - link indisponível" em notícias antigas:
  é normal, links de anos atrás frequentemente saem do ar.

## Passo a passo para instalar (ambiente real)

### 1. Criar a conta de serviço do Google
1. Acesse [console.cloud.google.com](https://console.cloud.google.com/) e crie um projeto.
2. Ative a **Google Sheets API** (menu "APIs e serviços" → "Ativar APIs e serviços").
3. Em "Credenciais" → "Criar credenciais" → "Conta de serviço".
4. Na conta de serviço criada, vá em "Chaves" → "Adicionar chave" → **JSON** → baixe o arquivo.
5. Abra a planilha da ACS → "Compartilhar" → cole o e-mail que está dentro do JSON (formato `nome@projeto.iam.gserviceaccount.com`) → permissão de **Editor**.

### 2. Criar o repositório no GitHub
1. Crie um repositório novo (pode ser privado) em github.com.
2. Suba todo o conteúdo desta pasta para ele — veja "Como criar a pasta `.github/workflows/`" abaixo se tiver dúvida nesse passo.

### 3. Cadastrar a credencial como secret
No repositório: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`.
- Nome: `GOOGLE_SERVICE_ACCOUNT_JSON`
- Valor: cole o **conteúdo inteiro** do arquivo JSON baixado no passo 1.

### 4. Pronto — conferir se está rodando
O workflow já está configurado para rodar sozinho às 8h, 12h e 18h
(horário da Bahia). Para testar na hora, sem esperar o horário agendado:
vá em `Actions` → `Clipping UFSB (3x ao dia)` → `Run workflow`.

Acompanhe o log da execução: ele mostra quantas notícias foram
encontradas, quantas foram enviadas ao Clipping, quantas foram
ignoradas e quantas deram erro de link.

## Como criar a pasta `.github/workflows/`

Não precisa criar manualmente — ao subir a pasta inteira do projeto
(passo 2 acima), ela já vem pronta. Duas formas de subir:

- **Arrastar e soltar**: no repositório vazio, "Add file" → "Upload
  files", e arraste a pasta do projeto inteira para a área de upload. O
  navegador preserva a estrutura de pastas do disco, inclusive a
  `.github`, mesmo que ela apareça oculta no Finder/Explorer.
- **Se isso não pegar a pasta oculta**: "Add file" → "Create new file"
  e digite o caminho completo no campo de nome:
  `.github/workflows/clipping-diario.yml` — o GitHub cria as pastas na
  hora, a cada `/` digitado. Depois é só colar o conteúdo desse arquivo.

## Testando sem tocar na planilha real

Antes de rodar contra a planilha de verdade, dá pra conferir que a
lógica está funcionando com dados fictícios:

```bash
pip install -r requirements.txt
python testar_simulacao.py
```

Isso simula um lote de notícias (algumas sobre UFSB, uma irrelevante, uma
com link quebrado, uma que já existiria no Clipping) e mostra exatamente
o que seria gravado — sem acessar a internet nem o Google Sheets.

## Rodando manualmente contra a planilha real (opcional, para depurar)

```bash
pip install -r requirements.txt
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat caminho/para/credenciais.json)"
python pipeline.py
```

## Ajustando o que conta como "sobre a UFSB" ou os temas/campi

Tudo isso fica em `config.py`:
- `UFSB_KEYWORDS`: termos que definem relevância.
- `TEMA_KEYWORDS` / `CAMPUS_KEYWORDS`: regras de categorização.
- `LOTE_MAXIMO_POR_EXECUCAO`: quantas notícias pendentes processar por execução.

## Coleta complementar opcional

O projeto também inclui `coleta.py`, um coletor via Google News RSS que
não depende de "List of All Alerts". Ele fica desligado por padrão — o
pipeline principal (`pipeline.py`) não o chama. Se no futuro vocês
quiserem uma segunda fonte de notícias além da já existente, ele está
pronto para ser plugado; é só pedir ajuda para integrar.

## Próximo passo: o relatório visual

Com a aba "clipping tratado" sendo alimentada, conecte o Looker Studio
direto na planilha (Looker Studio → Novo relatório → Fonte de dados →
Planilhas Google). Nenhuma linha de código necessária. Se preferirem,
também posso montar esse relatório com vocês.
