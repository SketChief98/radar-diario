# Radar Diário

Dashboard responsiva em português de Portugal, com exatamente cinco histórias por edição, Portugal primeiro, filtros de categoria, arquivo por data, fontes, separação entre factos e análise e destaque de riscos.

## O que faz a atualização automática

O workflow `.github/workflows/pages.yml` corre todos os dias às **09:00, hora de Lisboa**, pesquisa notícias recentes através da pesquisa web da API OpenAI, valida a estrutura das cinco histórias, acrescenta a edição ao arquivo e publica o site no GitHub Pages. O próprio workflow faz a geração e a publicação; não depende de um segundo agendamento.

Para reduzir erros, se a pesquisa falhar, se faltar uma fonte ou se o modelo não devolver exatamente cinco histórias válidas, a execução termina sem publicar uma edição parcial. Se a página da fonte fornecer uma imagem Open Graph, o workflow usa-a; caso contrário, usa uma imagem ilustrativa temática. A imagem de cada artigo poderá não estar disponível em todas as fontes.

## Ativação única necessária

1. **Pausa a automação anterior das 09:00** na aplicação onde foi criada. Não consegui localizá-la nem alterá-la a partir desta sessão; a pausa evita dois briefings quando o novo fluxo for ativado.
2. Crie um repositório GitHub chamado, por exemplo, `radar-diario`, e envie **o conteúdo desta pasta** para a branch `main`.
3. Em **Settings → Pages**, selecione **GitHub Actions** como origem.
4. Em **Settings → Secrets and variables → Actions**, crie o segredo `OPENAI_API_KEY` com uma chave da API OpenAI. A chave fica no GitHub como segredo; nunca a coloque nos ficheiros ou nesta conversa. A API é faturada separadamente da subscrição ChatGPT e o custo varia com o modelo e a pesquisa web.
5. Em **Settings → Actions → General → Workflow permissions**, permita que workflows leiam e escrevam no repositório. Isto permite ao fluxo guardar cada edição no arquivo.
6. Em **Settings → Secrets and variables → Actions → Variables**, crie a variável `AUTO_PUBLISH_ENABLED` com o valor `true`. Sem esta variável, os agendamentos ficam inativos.
7. Em **Actions**, execute uma vez **Atualizar e publicar Radar Diário** com **Run workflow**. A primeira execução manual gera a edição do dia e publica o site. Depois, as edições diárias correm automaticamente.

O site só fica online depois da configuração de Pages e do repositório. O URL será mostrado em **Settings → Pages**.

## Briefing anterior às 09:00

Este workflow substitui a automação diária anterior, para não gerar dois briefings. Só ativa `AUTO_PUBLISH_ENABLED` depois de pausares o agendamento anterior. A variável funciona como interruptor: se for removida ou alterada para outro valor, os agendamentos deixam de gerar notícias.

## Arquivo e edição manual

As edições são guardadas em `data/editions.json`, uma por data. O site escolhe automaticamente a mais recente. Para corrigir ou acrescentar uma edição à mão, edita o JSON e envia a alteração para `main`; o workflow publica a página. Mantém exatamente cinco histórias, com uma ou mais de Portugal no início e ligações diretas às fontes.

Cada história contém `region`, `category`, `title`, `published`, `facts`, `whyItMatters`, `analysis`, `risks`, `sourceName` e `sourceUrl`. As imagens, textos alternativos e créditos são preenchidos pelo gerador.

## Fiabilidade e custos

O agendamento do GitHub Actions pode ocasionalmente começar com atraso em períodos de carga. A geração usa `gpt-6.1-sol` com pesquisa web e pode incorrer em custos da API OpenAI. Não há garantias de que todas as páginas de notícias exponham uma imagem para reutilização; nesse caso, usa-se uma imagem ilustrativa Unsplash. Os links de notícias abrem no site original.
