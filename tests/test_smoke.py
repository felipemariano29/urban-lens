import os
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def test_api_healthcheck():
    """Valida o healthcheck principal e a disponibilidade dos containers."""
    response = requests.get(f"{API_URL}/api/v1/health", timeout=5)
    assert response.status_code == 200, "API FastAPI offline!"

def test_fluxo_ingestao():
    """Valida se o pipeline de ingestão Medallion (Bronze/Silver) carrega sem erros fatais."""
    result = subprocess.run(
        ["python", "pipelines/ingest_manual.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "O script do fluxo de ingestão quebrou ou não foi encontrado!"

def test_fluxo_indexacao():
    """Valida se o motor de indexação de embeddings e Milvus carrega sem erros."""
    result = subprocess.run(
        ["python", "-m", "urban_lens.cli.index_docs", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "O script do fluxo de indexação falhou na inicialização!"

def test_api_query_endpoint():
    """Valida a rota /query com payload vazio, enviando credenciais de RBAC."""
    api_key = os.getenv("URBAN_LENS_INTERNAL_API_KEY", "chave_padrao_se_falhar")
    
    print(f"\n[DEBUG] Enviando chave: {api_key}")
    
    headers = {
        "x-profile-name": "admin",
        "x-api-key": api_key,
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.post(f"{API_URL}/api/v1/chat/query", json={}, headers=headers, timeout=5)
    
    assert response.status_code == 422, f"Status: {response.status_code} - Resposta: {response.text}"

def test_api_metadata_endpoint():
    """Valida a rota /metadata testando se o router de governança responde."""
    response = requests.options(f"{API_URL}/api/v1/metadata", timeout=5)
    assert response.status_code != 404, "A rota de /metadata não foi encontrada no servidor!"

def test_interface_health():
    """Valida se o Front-end (Next.js) está servindo as páginas HTML."""
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        assert response.status_code == 200, "Front-end offline ou com erro interno (500)!"
    except requests.exceptions.ConnectionError:
        assert False, "Não foi possível conectar ao Front-end na porta 3000."