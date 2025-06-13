"""Builds a registry for the IEF project."""

import getpass
import logging
import sys
from pathlib import Path

import click
from pydantic import BaseModel, computed_field

from torc import (
    make_api,
    add_jobs,
)
from torc.config import torc_settings
from torc.loggers import setup_logging
from torc.openapi_client import (
    ComputeNodeResourceStatsModel,
    DefaultApi,
    FileModel,
    JobModel,
    ResourceRequirementsModel,
    SlurmSchedulerModel,
    WorkflowModel,
)


logger = logging.getLogger(__name__)

DSGRID_CLI = "dsgrid-cli.py"
SLURM_ACCOUNT = "dsgrid"
SCRIPT_BASE_DIR = Path(__file__).parent
START_SPARK_CLUSTER = "bash " + str(SCRIPT_BASE_DIR / "start_spark_cluster.sh")
SPARK_SUBMIT_COMMAND = "bash " + str(SCRIPT_BASE_DIR / "spark_submit_wrapper.sh")
DSGRID_RUN_COMMAND = "bash " + str(SCRIPT_BASE_DIR / "run_dsgrid_command.sh")


class RegistryParams(BaseModel):
    data_dir: Path
    db_file: Path

    def data_file(self) -> Path:
        return self.data_dir / "registry.json5"

    def get_sqlite_url(self) -> str:
        return f"sqlite:///{self.db_file}"

    def get_dataset_record_file(self, dataset_id: str, version: str = "1.0.0") -> Path:
        return (
            self.data_dir / "data" / dataset_id / version / "load_data.parquet" / "._SUCCESS.crc"
        )

    def get_derived_dataset_record_file(self, dataset_id: str, version: str = "1.0.0") -> Path:
        return self.data_dir / "data" / dataset_id / version / "table.parquet" / "._SUCCESS.crc"


class RepoParams(BaseModel):
    base_dir: Path

    @computed_field
    def registration_file(self) -> Path:
        return self.base_dir / "build_registry" / "project_registration.json5"

    @staticmethod
    def list_dataset_ids() -> list[str]:
        return [
            "eia_861_annual_energy_use_state_sector",
            "ief_2025_buildings",
            "ief_2025_buildings_state",
            "ief_2025_dgen",
            "ief_2025_industry",
            "ief_2025_transport",
        ]

    def get_mapped_dataset_query_file(self, dataset_id: str) -> Path:
        return self.base_dir / "build_registry" / "dataset_query_files" / f"{dataset_id}.json5"


class QueryParams(BaseModel):
    base_dir: Path

    def get_query_output_record_file(self, name: str) -> Path:
        return self.base_dir / name / "table.parquet" / "._SUCCESS.crc"

    def get_query_output_dir(self) -> Path:
        return self.base_dir / "query_output"


class IefRegistry(BaseModel):
    """Defines parameters for the IEF registry."""

    registry: RegistryParams
    repo: RepoParams
    input_dataset_base_dir: Path
    query: QueryParams


def create_workflow(api: DefaultApi) -> WorkflowModel:
    """Creates a workflow with implicit job dependencies declared through files."""
    workflow = WorkflowModel(
        user=getpass.getuser(),
        name="build_ief_registry",
        description="Build IEF registry",
    )
    return api.add_workflow(workflow)


def build_workflow(api: DefaultApi, workflow: WorkflowModel, ief: IefRegistry) -> None:
    config = api.get_workflow_config(workflow.key)
    config.compute_node_resource_stats = ComputeNodeResourceStatsModel(
        cpu=True,
        memory=True,
        process=True,
        interval=5,
        monitor_type="periodic",
        make_plots=True,
    )
    # TODO: implement a feature in torc to check software/data versions and trigger re-runs.
    # TODO add a check to ensure this exists
    # TODO add a check to ensure that invocation scripts exist
    config.worker_startup_script = START_SPARK_CLUSTER
    api.modify_workflow_config(workflow.key, config)

    api.add_slurm_scheduler(
        workflow.key,
        SlurmSchedulerModel(
            name="dsgrid_registry",
            account=SLURM_ACCOUNT,
            nodes=2,
            walltime="04:00:00",
            mem="240G",
            ntasks_per_node=104,
            extra="-C lbw",
        ),
    )

    registry_data_file = api.add_file(
        workflow.key,
        FileModel(
            name="registry_data_file",
            path=str(ief.registry.data_file),
        ),
    )
    dataset_record_files, query_files, query_record_files = add_files_to_workflow(api, workflow, ief)
    add_jobs_to_workflow(
        api,
        workflow,
        ief,
        registry_data_file,
        dataset_record_files,
        query_files,
        query_record_files,
    )

    # TODOs:
    # - There is no mechanism to replace a dataset if the dataset config, dimensions, mapping,
    #   or project requirements change. That might be challenging.
    print(f"Created workflow {workflow.key}")


def add_files_to_workflow(
    api: DefaultApi, workflow: WorkflowModel, ief: IefRegistry
) -> tuple[dict[str, FileModel], dict[str, FileModel], dict[str, FileModel]]:
    dataset_record_files: dict[str, FileModel] = {}
    query_files: dict[str, FileModel] = {}
    query_record_files: dict[str, FileModel] = {}
    for dataset_id in ief.repo.list_dataset_ids():
        dfile = api.add_file(
            workflow.key,
            FileModel(
                name=f"{dataset_id}_record",
                path=str(ief.registry.get_dataset_record_file(dataset_id)),
            ),
        )
        assert dfile.id is not None
        qfile = api.add_file(
            workflow.key,
            FileModel(
                name=f"{dataset_id}_query",
                path=str(ief.repo.get_mapped_dataset_query_file(dataset_id)),
            ),
        )
        q_record_file = api.add_file(
            workflow.key,
            FileModel(
                name=f"mapped_{dataset_id}_record",
                path=str(ief.query.get_query_output_record_file(dataset_id)),
            ),
        )
        assert qfile.id is not None
        dataset_record_files[dataset_id] = dfile
        query_files[dataset_id] = qfile
        query_record_files[dataset_id] = q_record_file

    return dataset_record_files, query_files, query_record_files


def add_jobs_to_workflow(
    api: DefaultApi,
    workflow: WorkflowModel,
    ief: IefRegistry,
    registry_data_file: FileModel,
    dataset_record_files: dict[str, FileModel],
    query_files: dict[str, FileModel],
    query_output_record_files: dict[str, FileModel],
) -> None:
    rr_short = api.add_resource_requirements(
        workflow.key,
        ResourceRequirementsModel(
            name="short",
            num_cpus=100,
            memory="1g",
            runtime="P0DT30M",
        ),
    )
    rr_medium = api.add_resource_requirements(
        workflow.key,
        ResourceRequirementsModel(
            name="medium",
            num_cpus=100,
            memory="1g",
            runtime="P0DT1H",
        ),
    )
    rr_long = api.add_resource_requirements(
        workflow.key,
        ResourceRequirementsModel(
            name="long",
            num_cpus=100,
            memory="1g",
            runtime="P0DT1H",
            #runtime="P0DT4H",
        ),
    )
    dataset_params = {
        "eia_861_annual_energy_use_state_sector": {
            "rr": rr_short.id,
            "shuffle_partitions": 100,
        },
        "ief_2025_buildings": {
            "rr": rr_long.id,
            "shuffle_partitions": 2400,
        },
        "ief_2025_buildings_state": {
            "rr": rr_long.id,
            "shuffle_partitions": 2400,
        },
        "ief_2025_dgen": {
            "rr": rr_long.id,
            "shuffle_partitions": 1200,
        },
        "ief_2025_industry": {
            "rr": rr_long.id,
            "shuffle_partitions": 2400,
        },
        "ief_2025_transport": {
            "rr": rr_long.id,
            "shuffle_partitions": 2400,
        },
    }
    url = ief.registry.get_sqlite_url()
    query_output = ief.query.get_query_output_dir()
    build_registry_command = [
        "spark-submit",
        f"--conf=\"spark.sql.shuffle.partitions=1200\"",
        DSGRID_CLI,
        "-u",
        url,
        "registry",
        "bulk-register",
        "--base-repo-dir",
        str(ief.repo.base_dir),
        "--base-data-dir",
        str(ief.input_dataset_base_dir),
        str(ief.repo.registration_file),
    ]
    jobs = [
        JobModel(
            name="create_registry",
            command=f"dsgrid-admin create-registry {url} -p {ief.registry.data_dir} --overwrite",
            invocation_script=DSGRID_RUN_COMMAND,
            cancel_on_blocking_job_failure=True,
            output_files=[registry_data_file.id],
            resource_requirements=rr_short.id,
        ),
        JobModel(
            name="build_registry",
            command=" ".join(build_registry_command),
            invocation_script=SPARK_SUBMIT_COMMAND,
            cancel_on_blocking_job_failure=True,
            input_files=[registry_data_file.id],
            output_files=[x.id for x in dataset_record_files.values()],
            resource_requirements=rr_long.id,
        ),
    ]
    for dataset_id in ief.repo.list_dataset_ids():
        d_record_file = dataset_record_files[dataset_id]
        q_file = query_files[dataset_id]
        q_output_record_file = query_output_record_files[dataset_id]
        partitions = dataset_params[dataset_id]["shuffle_partitions"]
        cmd = [
            "spark-submit",
            f"--conf=\"spark.sql.shuffle.partitions={partitions}\"",
            f"{DSGRID_CLI} -u {url}",
            "query",
            "project",
            "run",
            q_output_record_file.path,
            "-o",
            str(query_output),
        ]
        job = JobModel(
            name=f"make_mapped_{dataset_id}",
            command=" ".join(cmd),
            invocation_script=SPARK_SUBMIT_COMMAND,
            cancel_on_blocking_job_failure=True,
            input_files=[d_record_file.id, q_file.id],
            output_files=[q_output_record_file.id],
            resource_requirements=dataset_params[dataset_id]["rr"],
        )
        jobs.append(job)

    add_jobs(api, workflow.key, jobs)


@click.command()
@click.option(
    "-r",
    "--ief-repo-dir",
    type=click.Path(exists=True),
    required=True,
    callback=lambda *x: Path(x[2]),
    help="IEF repository directory",
)
@click.option(
    "-d",
    "--ief-input-dataset-dir",
    type=click.Path(exists=True),
    required=True,
    callback=lambda *x: Path(x[2]),
    help="IEF base directory for input datasets",
)
@click.option(
    "-R",
    "--registry-base-dir",
    type=click.Path(exists=True),
    required=True,
    callback=lambda *x: Path(x[2]),
    help="Base directory for the IEF registry",
)
@click.option(
    "-q",
    "--query-base-dir",
    type=click.Path(exists=True),
    required=True,
    callback=lambda *x: Path(x[2]),
    help="Base directory for query outputs",
)
@click.option(
    "-o",
    "--overwrite",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite any files that already exist.",
)
def create_ief_workflow(
    ief_repo_dir: Path,
    ief_input_dataset_dir: Path,
    registry_base_dir: Path,
    query_base_dir: Path,
    overwrite: bool,
) -> None:
    """Create a Torc workflow that builds the IEF registry with its derived datasets."""
    setup_logging(__name__)
    if torc_settings.database_url is None:
        logger.error(
            "There is no torc config file or the database URL is not defined. "
            "Please fix the config file or define the URL in this script."
        )
        sys.exit(1)

    api = make_api(torc_settings.database_url)
    registry = IefRegistry(
        registry=RegistryParams(
            data_dir=(registry_base_dir / "registry-data").absolute(),
            db_file=(registry_base_dir / "registry.db").absolute(),
        ),
        repo=RepoParams(base_dir=ief_repo_dir),
        input_dataset_base_dir=ief_input_dataset_dir,
        query=QueryParams(base_dir=query_base_dir),
    )
    workflow = create_workflow(api)
    try:
        build_workflow(api, workflow, registry)
    except Exception:
        logger.exception("Failed to build workflow")
        api.remove_workflow(workflow.key)
        raise


if __name__ == "__main__":
    create_ief_workflow()
