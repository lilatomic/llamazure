import pytest

from llamazure.test.credentials import load_credentials


@pytest.fixture()
@pytest.mark.integration
def credentials():
	return load_credentials()
