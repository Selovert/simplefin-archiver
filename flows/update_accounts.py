
from prefect import flow
from prefect.logging import get_run_logger

@flow(name="update_accounts")
def update_accounts():
    _logger = get_run_logger()
    _logger.info("test")
    print("test")

if __name__ == "__main__":
    # creates a deployment and starts a long-running
    # process that listens for scheduled work
    update_accounts.serve(
        name="simplefin-update-accounts",
        tags=["simplefin"],
    )
