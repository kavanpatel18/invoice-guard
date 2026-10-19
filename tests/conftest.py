import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from invoiceguard.data_gen import generate_dataset
from invoiceguard.tools import load_policy


@pytest.fixture(scope="session")
def ds():
    return generate_dataset(42)


@pytest.fixture(scope="session")
def policy():
    return load_policy()


def first(ds, anomaly):
    return next(i for i in ds["invoices"] if ds["ground_truth"][i["invoice_id"]]["anomaly"] == anomaly)
