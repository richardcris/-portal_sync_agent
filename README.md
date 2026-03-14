# Portal do Contador - Agente de Sincronização

Este projeto monitora uma pasta local no Windows e envia automaticamente arquivos XML/NFC-e para o seu portal.

## O que ele faz
- monitora uma pasta e subpastas
- identifica novos arquivos `.xml`
- espera o arquivo terminar de ser gravado
- envia o arquivo para a API do portal
- move os arquivos enviados para `enviados`
- move arquivos com erro para `erros`
- permite teste manual de upload
- exibe Nome da empresa e CNPJ no painel lateral
- verifica atualização por manifesto JSON remoto

## Ajustes que você precisa fazer no seu site
Seu backend precisa ter um endpoint HTTP que receba `multipart/form-data` com estes campos:

- `file`: arquivo XML
- `companyId`: id da empresa
- `documentType`: `xml` ou `nfce_xml`
- `originalFileName`: nome original do arquivo

### Headers enviados
- `Authorization: Bearer SEU_TOKEN`
- `X-Company-Id: EMPRESA_123`

## Exemplo de rota esperada no backend
- URL base: `https://seu-dominio.com/api`
- endpoint: `/documents/upload`

## Como gerar o executável
1. instale Python 3.11 ou 3.12 no Windows
2. abra a pasta do projeto
3. execute `build_exe.bat`
4. o `.exe` será gerado em `dist/VEXPER-SISTEMAS.exe`

## Como gerar o instalador profissional
1. instale o Inno Setup 6 no Windows
2. gere o executável com `build_exe.bat`
3. execute `build_setup.bat`
4. o instalador será gerado em `dist/VEXPER-SISTEMAS-Setup.exe`

## Release automática para todos os agentes
Agora o projeto possui pipeline em `.github/workflows/release.yml`.

1. cada push no branch `main` gera nova release automaticamente
2. o workflow compila `VEXPER-SISTEMAS.exe` e `VEXPER-SISTEMAS-Setup.exe`
3. o workflow publica `manifest.json` na release
4. no cliente, use a URL fixa:
	`https://github.com/<usuario>/<repo>/releases/latest/download/manifest.json`

Quando um agente abrir o aplicativo, ele detecta a nova versão e aplica a atualização automática.

### Assinatura digital e checksum
O workflow já está preparado para assinatura e validação corporativa:

1. se os secrets existirem, os binários serão assinados automaticamente
2. é gerado o arquivo `dist/SHA256SUMS.txt` e publicado na release
3. o `manifest.json` inclui `setup_sha256` para conferência

Secrets necessários no GitHub (Repository Secrets):

1. `WIN_CERT_PFX_BASE64`: conteúdo Base64 do certificado `.pfx`
2. `WIN_CERT_PASSWORD`: senha do certificado

Se os secrets não forem informados, a release continua funcionando, porém sem assinatura digital.

## Metodo facil de atualizacao publica
Se quiser publicar sem depender de GitHub Actions, use o comando local:

1. execute `publicar_atualizacao.bat`
2. informe versao, URL publica base e notas
3. o script sincroniza automaticamente o `APP_VERSION` no codigo
4. o script gera build + setup + manifesto usando a mesma versao
5. suba a pasta `public_update` para seu hosting (CDN, servidor web, S3, etc.)

Isso evita divergencia entre versao do executavel instalado e versao publicada no `manifest.json`.

Depois configure os agentes com:

`https://seu-host/public_update/latest/manifest.json`

Arquivos gerados automaticamente:

1. `public_update/latest/VEXPER-SISTEMAS-Setup.exe`
2. `public_update/latest/manifest.json`
3. `public_update/latest/SHA256SUMS.txt`
4. `public_update/versions/<versao>/...`

## Manifesto de atualização (exemplo)
Configure o campo "URL de atualização" para apontar para um JSON no formato:

```json
{
	"version": "1.1.0",
	"download_url": "https://seu-dominio.com/downloads/VEXPER-SISTEMAS-Setup.exe",
	"notes": "Correções e melhorias."
}
```

## Observação importante
Eu não consigo compilar um `.exe` Windows real aqui dentro do ambiente Linux da conversa. Então deixei o projeto pronto para você gerar em 1 clique no seu Windows com o `build_exe.bat`.

## Dica de API
Se o seu portal for Base44, adapte a rota do backend para salvar o documento no registro correto da empresa e validar o token antes de aceitar o upload.
