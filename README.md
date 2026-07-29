# chapkit-ewars-malaria

> Adaptação do [chapkit_ewars_model](https://github.com/chap-models/chapkit_ewars_model) (modelo WHO EWARS em Bayesian INLA) para previsão de casos de **Malária**, com humidade relativa como covariável adicional e lags configurados especificamente para malária.

## Visão geral

Este serviço prevê casos de malária a nível distrital, integrando-se ao **chap-core / DHIS2** da mesma forma que o modelo EWARS original: o chap-core descobre o serviço via `GET /api/v1/info` e conduz o treino/previsão via REST, sem ficheiros de configuração YAML nem adaptadores externos.

A diferença para o modelo original está apenas na **configuração do modelo**, não na lógica interna do INLA:

| Covariável | Papel no modelo | Lag (meses) |
|---|---|---|
| `population` | offset (obrigatória, sem lag) | — |
| `rainfall` (precipitação) | preditor com lag | 1 |
| `mean_temperature` (temperatura) | preditor com lag | 1 |
| `relative_humidity` (humidade relativa) | preditor com lag — **novo** | 3 |

A humidade relativa foi adicionada porque influencia diretamente o ciclo de vida do mosquito *Anopheles* e a sobrevivência do parasita, com efeito habitualmente mais desfasado no tempo do que a chuva ou a temperatura — daí o lag maior (3 meses).

## O que foi alterado

1. **`main.py`** — os valores por omissão do `EwarsConfig` passaram a incluir `relative_humidity` em `additional_continuous_covariates`, e `n_lags` passou a `[1, 1, 3]` (mesma ordem: rainfall, mean_temperature, relative_humidity).
2. **Dados de entrada** — os CSVs históricos e futuros precisam de uma coluna `relative_humidity`, além das colunas já exigidas pelo modelo original (`time_period`, `rainfall`, `mean_temperature`, `disease_cases`, `population`, `location`).
3. **Nada mudou no código R** (`scripts/predict.R`) — o modelo já constrói a base `dlnm` dinamicamente a partir da lista de covariáveis da configuração, por isso a humidade relativa e os novos lags funcionam sem alterar a lógica estatística.

## Estrutura de dados esperada

**Histórico / treino:**

| Coluna | Tipo | Nota |
|---|---|---|
| `time_period` | texto | ex.: `2024-03` |
| `rainfall` | número | precipitação |
| `mean_temperature` | número | temperatura média |
| `relative_humidity` | número | humidade relativa — **nova** |
| `disease_cases` | inteiro | casos de malária (variável alvo) |
| `population` | inteiro | usada como offset |
| `location` | texto | id espacial (distrito) |

**Dados futuros:** mesma estrutura, com `disease_cases` em branco/NA para os períodos a prever.

**Saída (`predictions.csv`):** 1000 amostras posteriores por linha (`sample_0` … `sample_999`), igual ao modelo original.

## Como executar

```bash
# imagem pré-construída
docker compose -f compose.ghcr.yml up

# ou build local
make build
make run
```

O serviço fica disponível em `http://localhost:8000`:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/info
```

## Ajustar covariáveis ou lags sem alterar código

Como o chap-core permite covariáveis contínuas livres, é possível testar outra combinação de covariáveis/lags em tempo de execução, sem tocar no `main.py`, via:

```
POST /api/v1/configs
{
  "additional_continuous_covariates": ["rainfall", "mean_temperature", "relative_humidity"],
  "n_lags": [1, 1, 3]
}
```

Isto é útil para testes rápidos; para a configuração passar a ser a predefinida do serviço (o que a equipa normalmente quer numa instância de produção), deve continuar a ser feita a alteração dos valores por omissão diretamente no `main.py`, como já está nesta versão.

## Créditos

Baseado no modelo WHO EWARS (Early Warning, Alert and Response System), adaptado pelo HISP Centre / Universidade de Oslo como parte da plataforma CHAP. Esta versão foi adaptada pela Saudigitus para o contexto da vigilância de malária.

## Licença

GPL v3 (herdada do repositório original).
