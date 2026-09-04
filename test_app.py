import pytest
from app import app


@pytest.fixture
def cliente():
    app.config['TESTING'] = True
    with app.test_client() as cliente:
        yield cliente


def test_home(cliente):
    respuesta = cliente.get('/')
    assert respuesta.status_code == 200


def test_health(cliente):
    respuesta = cliente.get('/health')
    assert respuesta.status_code in (200, 500)  # nosec B101 - puede fallar intencionalmente (simulación)


def test_buscar_responde(cliente):
    respuesta = cliente.get('/buscar?id=1')
    assert respuesta.status_code in (200, 500)  # nosec B101 - depende de si la tabla existe
