import os
from pathlib import Path

from chapkit import BaseConfig
from chapkit.api import AssessedStatus, MLServiceBuilder, MLServiceInfo, ModelMetadata, PeriodType
from chapkit.artifact import ArtifactHierarchy
from chapkit.ml import ShellModelRunner
from pydantic import Field


class EwarsConfig(BaseConfig):
    prediction_periods: int = Field(
        default=4,
        description="Number of periods to predict into the future",
    )
    n_lags: list[int] = Field(
        default_factory=lambda: [1,1,3],
        description=(
            "Number of lags per covariate, in the same order as "
            "additional_continuous_covariates. A single-element list "
            "broadcasts to all covariates."
        ),
    )
    precision: float = Field(
        default=0.01,
        description="Prior on the precision of fixed effects. Works as regularization",
    )
    region_seasonal: bool = Field(
        default=False,
        description="Optional inclusion of region specific seasonal effects",
    )
    # BaseConfig reserves `additional_continuous_covariates` as a CHAP-interpreted
    # field. scripts/predict.R reads it into `covariate_names` and wires those
    # columns into `generate_lagged_model`. The default here makes EWARS use
    # rainfall + mean_temperature out of the box (matching the legacy model).
    # Deployments that don't have climate data can override per-config via
    # POST /api/v1/configs with additional_continuous_covariates=[] to run
    # the population-only variant without forking this repo.
    additional_continuous_covariates: list[str] = Field(
    default_factory=lambda: ["rainfall", "mean_temperature", "relative_humidity"],
        description=(
            "Continuous covariates to include as lagged predictors in the INLA model. "
            "Defaults match the legacy CHAP-EWARS model which used rainfall and "
            "mean_temperature. Override via POST /api/v1/configs to run with a "
            "different covariate set."
        ),
    )


runner: ShellModelRunner[EwarsConfig] = ShellModelRunner(
    train_command="Rscript scripts/train.R --data {data_file}",
    predict_command=(
        "Rscript scripts/predict.R --historic {historic_file} --future {future_file} --output {output_file}"
    ),
)

info = MLServiceInfo(
    id="malaria-mensal-ewars",
    display_name=" Malaria EWARS Model (Saudigitus)",
    version="1.0.0",
    description=(
        "Uma re-adaptação do modelo EWARS da OMS, desenvolvido pela equipe CHAP core."
        "Este modelo é uma implementação para modelagem e previsão de casos de malária. "
        "O EWARS é um modelo hierárquico Bayesiano implementado com a biblioteca INLA."
    ),
    model_metadata=ModelMetadata(
        author="Fernando Inácio",
        author_assessed_status=AssessedStatus.orange,
        organization="Saudigitus, Serviços de Saúde Digital",
        organization_logo_url="",
        contact_email="finacio@saudigitus.org",
        citation_info=(
            '2026. "Malaria-EWARS model". '
            "Saudigitus. "
        ),
    ),
    period_type=PeriodType.monthly,
    allow_free_additional_continuous_covariates=True,
    required_covariates=["population"],
    min_prediction_periods=0,
    max_prediction_periods=100,
)

hierarchy = ArtifactHierarchy(
    name="ewars",
    level_labels={0: "ml_training_workspace", 1: "ml_prediction"},
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/chapkit.db")
if DATABASE_URL.startswith("sqlite") and ":///" in DATABASE_URL:
    db_path = Path(DATABASE_URL.split("///")[1])
    db_path.parent.mkdir(parents=True, exist_ok=True)

app = (
    MLServiceBuilder(
        info=info,
        config_schema=EwarsConfig,
        hierarchy=hierarchy,
        runner=runner,
        database_url=DATABASE_URL,
    )
    .with_registration(keepalive_interval=15)
    .build()
)
