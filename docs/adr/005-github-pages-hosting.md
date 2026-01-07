# ADR-005: GitHub Pages som hosting för webbplatsen

## Status

Accepterad

## Kontext och problembeskrivning

För att publicera de genererade HTML-filerna av SFS-författningar behövde vi välja en hosting-lösning. Projektet genererar statiska HTML-filer som behöver vara publikt tillgängliga på webben.

Huvudalternativen var:

1. **GitHub Pages**: Hosting direkt via GitHub
2. **Cloudflare R2**: Object storage med HTTP-access
3. **Cloudflare R2 + Workers**: Object storage med serverless rewrites
4. **Docker Container**: Containeriserad webserver (nginx/Apache)
5. **Amazon CloudFront + S3**: CDN med S3 object storage
6. **Traditionell hosting**: VPS eller shared hosting

Utmaningarna var:

- **Kostnad**: Projektet har ingen budget för hosting
- **Enkelhet**: Lösningen ska vara enkel att sätta upp och underhålla
- **Integration**: Bör fungera smidigt med befintlig GitHub-baserad workflow
- **Suveränitet**: Beroende av externa tjänster
- **URL-hantering**: Behov av att `selex.se/folder/` automatiskt servar `index.html`
- **Migrering**: Möjlighet att flytta till annan lösning om behov uppstår

## Beslut

Vi använder **GitHub Pages** som primär hosting-lösning för den genererade HTML-webbplatsen.

### Arkitektur

```text
GitHub Actions Workflow
    ↓
Genererar HTML-filer (alt. ladda ner från R2)
    ↓
Skapar Pages artifact
    ↓
Deploy till GitHub Pages
    ↓
Publik webbplats (https://selex.se)
```

### Backup-lösning

Cloudflare R2 används som backup och alternativ hosting:

- HTML-filer synkas även till R2 bucket
- Kan aktiveras som fallback vid problem med GitHub Pages
- Begränsning: Kräver Cloudflare Workers för fullständig funktionalitet (rewrites)

## Konsekvenser

### Positiva

- **Helt gratis**: GitHub Pages är kostnadsfritt för publika repositories
- **Enkel integration**: Seamless integration med GitHub-baserad workflow
  - Same platform som source code, issues, och pull requests
  - Automatisk deployment via GitHub Actions (redan konfigurerat)
  - Inget behov av externa credentials eller API-nycklar
- **Ingen infrastruktur**: Ingen server att underhålla eller uppdatera
- **Inbyggd CDN**: GitHub Pages använder CDN för snabb leverans globalt
- **HTTPS automatiskt**: SSL/TLS-certifikat hanteras automatiskt
- **URL-rewrites fungerar**: `selex.se/1999/1/` servar automatiskt `index.html`
- **Custom domain-stöd**: Möjlighet att använda egen domän
- **Artifact-baserad deployment**: Använder GitHub Actions artifacts för deployment
- **Enkel att förstå**: Lågtröskel för bidragsgivare att förstå deployment

### Negativa

- **Suveränitetsberoende**: Projektet är beroende av GitHubs tillgänglighet och villkor
  - Mitigering: GitHub är en stabil plattform med hög uptime
  - Mitigering: Enkel migrering (se nedan)

- **Begränsad kontroll**: Mindre flexibilitet än egen hosting
  - Kan inte köra server-side logic
  - Begränsade HTTP-headers och caching-policies
  - Mitigering: Statiska HTML-filer kräver inte server-side logic

- **GitHub-specifikt**: Lösningen är kopplad till GitHub som plattform
  - Mitigering: Projektet använder redan GitHub för allt annat
  - Mitigering: Automatiserad deployment gör migrering enkel

### Migrering är enkel

Eftersom vi bara publicerar statiska HTML-filer är migrering trivial:

- Generera HTML-filer via workflow eller lokalt
- Ladda upp till ny hosting-lösning
- Uppdatera DNS (om custom domain används)
- Cloudflare R2 backup finns redan som färdig alternativ lösning

Migreringstid: < 1 timme

## Alternativ som övervägdes

### 1. Cloudflare R2 (utan Workers)

**Fördelar**:

- Extremt billig storage (~$0.015/GB/månad)
- Ingen vendor lock-in till GitHub
- Egen kontroll över filer
- Redan implementerad som backup-lösning

**Varför inte valt som primär lösning**:

- **URL-rewrites fungerar inte**: `/folder/` servar inte automatiskt `index.html`
  - Problem: Användare måste besöka `/folder/index.html` explicit
  - Problemet gäller även för root: `selex.se/` fungerar inte
- Kräver manuell upload-process eller separat CI/CD
- Mer komplext att sätta upp än GitHub Pages
- Kräver hantering av Cloudflare-credentials

### 2. Cloudflare R2 + Workers

**Fördelar**:

- Löser URL-rewrite problemet via Workers
- Full kontroll över HTTP-routing och headers
- Kraftfull om avancerad logik behövs

**Varför inte valt**:

- **Kostnad**: Workers kostar $5/månad (minimum)
  - Projektet har ingen budget
- **Komplexitet**: Kräver Worker-kod för URL-rewrites
- **Overkill**: Statiska HTML-filer behöver inte serverless compute
- **Underhåll**: Ytterligare kod att underhålla

### 3. Docker Container med nginx/Apache

**Fördelar**:

- Full kontroll över konfiguration och deployment
- Portabelt - kan köras var som helst (lokalt, VPS, cloud)
- Standard webserver (nginx/Apache) hanterar URL-rewrites automatiskt
- Ingen vendor lock-in
- Kan köras gratis på många plattformar (Fly.io free tier, Railway, etc.)

**Varför inte valt**:

- **Hosting krävs fortfarande**: Container måste köras någonstans
  - Gratis alternativ finns men ofta med begränsningar
  - Kräver egen server eller cloud-plattform för produktion
- **Mer komplext deployment**: Container registry, orchestration, deployment
- **Underhåll**: Container images måste uppdateras och hanteras
- **CI/CD komplexitet**: Kräver byggsteg för container + push till registry + deployment
- **Overkill**: Container-infrastruktur är onödigt komplext för enbart statiska filer
- **Kostnad över tid**: Även "gratis" tiers har begränsningar, kan kräva betalning senare

### 4. Traditionell hosting (VPS/Shared hosting)

**Varför inte valt**:

- **Kostnad**: VPS kostar $5-20/månad, shared hosting $3-10/månad
- **Underhåll**: Kräver serveradministration, säkerhetsuppdateringar
- **Komplexitet**: Overkill för statiska filer
- **CI/CD**: Kräver SSH-credentials och deployment-scripts

### 5. Netlify/Vercel

**Fördelar**:

- Liknande fördelar som GitHub Pages
- Fler features (serverless functions, forms)

**Varför inte valt**:

- Ingen fördel för vårt användningsfall (bara statiska filer)
- Ytterligare extern tjänst att hantera
- GitHub Pages är enklare när allt redan finns på GitHub

### 6. Amazon CloudFront + S3

**Fördelar**:

- Kraftfull CDN med global presence (AWS edge locations)
- Billig storage i S3 (~$0.023/GB/månad)
- Bra om projektet redan använder AWS-ekosystemet
- Professionell lösning med SLA:er
- CloudFront free tier: 1 TB utgående data/månad första 12 månaderna

**Varför inte valt**:

- **URL-rewrites fungerar inte automatiskt**: Samma problem som Cloudflare R2
  - `/folder/` servar inte automatiskt `index.html`
  - CloudFront stödjer bara default root object för root, inte subdirectorier
  - Kräver CloudFront Functions eller Lambda@Edge för rewrites
- **Kostnad**:
  - CloudFront Functions: ~$0.10 per miljon requests
  - Lambda@Edge: Dyrare än CloudFront Functions
  - Efter free tier: Data transfer kostar (~$0.085/GB för första 10 TB)
- **Komplexitet**:
  - Kräver AWS-konto och hantering av credentials
  - CloudFront Functions eller Lambda@Edge kod måste skrivas och deployas
  - Mer komplext än GitHub Pages
- **AWS-specifikt**: Vendor lock-in till AWS-ekosystemet
- **Overkill**: Projektet har ingen budget och använder inte AWS för övrigt

**Alternativa S3 lösningar**:

- S3 Static Website Endpoint fungerar med automatiska rewrites, men kräver publik bucket (fungerar inte med CloudFront OAI/OAC för säker access)

## Relaterade beslut

- [ADR-001](001-markdown-som-mellanformat.md) - Markdown som mellanformat (genererar HTML-output)
- Workflow-konfiguration: `.github/workflows/github-pages-workflow.yml`

## Noteringar

- **Deployment-process**:

  ```yaml
  # GitHub Actions workflow (.github/workflows/github-pages-workflow.yml)
  1. Checkout code
  2. Generera HTML-filer till _site/ katalog (eller ladda från R2)
  3. Skapa Pages artifact via actions/upload-pages-artifact
  4. Deploy artifact via actions/deploy-pages
  5. GitHub Pages servar automatiskt från artifact
  ```

- **Cloudflare R2 backup**:
  - Filer synkas till R2 parallellt
  - Script: `tools/upload_to_cloudflare.py`
  - Kan aktiveras manuellt vid behov
  - Begränsning: URL-rewrites fungerar inte utan Workers

- **Framtida möjligheter**:
  - Custom domain kan adderas utan kod-ändringar
  - Kan byta till R2+Workers om budget tillkommer
  - Migrering till annan plattform är trivial (kopiera filer)

- **Performance**:
  - GitHub Pages använder Fastly CDN
  - Bra global latency
  - Automatisk gzip-kompression

- **Begränsningar** (GitHub Pages limits):
  - Max 1 GB repository size (långt ifrån vår användning)
  - Max 100 GB bandwidth/månad (mer än tillräckligt)
  - Max 10 builds/timme (vi bygger vid code changes)

- **Exempel på GitHub Pages URL-rewrites**:

  ```text
  /1999/1/          → /1999/1/index.html
  /1999/1/kapitel-1 → /1999/1/kapitel-1/index.html
  /                 → /index.html
  ```

  Detta fungerar automatiskt utan konfiguration.
