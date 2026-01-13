from prefect import flow

@flow(log_prints=True)
def hello(name: str = "Mr Buga") -> None:
    """Log a friendly greeting."""
    print(f"Hello, {name}!")