from invoke import task
import residual
import prediction
import RetrainAndBuild
import updates
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


@task
def calculate_residuals(ctx):
    try:
        residual.calc_res()
    except Exception as err:
        print(err)


@task()
def retrain(ctx):
    try:
        RetrainAndBuild.retrain()
    except Exception as err:
        print(err)


@task
def build(ctx):
    RetrainAndBuild.build_model()


@task()
def predict(ctx):
    try:
        prediction.predict()
        logging.info("update is starting")
        updates.check_for_updates()
    except Exception as err:
        print(err)
