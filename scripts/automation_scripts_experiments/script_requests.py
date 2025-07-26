import logging
import shutil
import subprocess
import os
from pathlib import Path
import re
import json
import requests
import time

# Configurações do SonarQube
SONAR_URL = "http://192.168.10.8:9000"
SONAR_TOKEN = "sqa_4db91a7c26b1b14ba7b150f125039e7563ed61fb"  # Use o token gerado no SonarQube

# Caminhos base e variáveis globais
project_path_base = Path("/media/pedrinho/MESTRADO/DISSERTACAO/Experimento_Final/project")
python_version = "3.11.0"
venv_name = "requests"

# Inicialmente essas variáveis serão atualizadas no loop
project_path = project_path_base / venv_name
project_path_pyenv = Path.home() / ".pyenv" / "versions" / venv_name
log_path = project_path / f'test_{venv_name}.log'
sonarqube_output_path = project_path / f'sonar_{venv_name}.json'
classification_output_path = project_path / f'classification_{venv_name}.txt'


def safe_copytree(src: Path, dst: Path, ignore_tests: bool = True):
    def ignore_patterns(path, names):
        if ignore_tests:
            ignored = [n for n in names if n == 'tests' or n.startswith('tests')]
            return set(ignored)
        return set()

    try:
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_patterns)
    except shutil.Error as e:
        print(f"[Aviso] Erros durante a cópia de arquivos: {e}")
    except FileNotFoundError as e:
        print(f"[Aviso] Diretório não encontrado: {e.filename}")


def run_batch_experiments(num_experiments=15):
    subprocess.run("fuser -k 50001/udp", shell=True, stderr=subprocess.DEVNULL)

    for i in range(1, num_experiments + 1):
        src_instance = project_path_base / f"requests_{i}"
        working_dir = project_path_base / "requests"
        completed_dir = project_path_base / f"requests_{i}_done"

        print("#################################################################")
        print(f"\n🔁 Iniciando experimento {i}: requests_{i}")
        print("#################################################################")

        if completed_dir.exists():
            print(f"⚠️ Excluindo {completed_dir} já existente.")
            shutil.rmtree(completed_dir)

        print(f"📁 Copiando {src_instance} para {working_dir} (ignorando pasta tests)")
        safe_copytree(src_instance, working_dir, ignore_tests=True)
        print(f"📁 Copiado {src_instance} para {working_dir}")

        global project_path, project_path_pyenv, log_path, sonarqube_output_path, classification_output_path
        project_path = working_dir
        project_path_pyenv = Path.home() / ".pyenv" / "versions" / venv_name
        log_path = project_path / f'test_{venv_name}.log'
        sonarqube_output_path = project_path / f'sonar-issues.json'
        classification_output_path = project_path / f'classification_{venv_name}.txt'

        try:
            prepare_environment()
            success = run_tests()
            if success:
                run_sonarqube(f"requests_{i}", project_path, venv_name)
                classify_sonarqube_issues()
            else:
                with open(classification_output_path, "a") as f:
                    f.write(f"Experimento {i}: Erro nos testes\n")
        except Exception as e:
            print(f"❌ Erro de execução no experimento {i}: {e}")
            with open(classification_output_path, "a") as f:
                f.write(f"Experimento {i}: Erro de execução - {e}\n")

        if working_dir.exists():
            shutil.move(str(working_dir), str(completed_dir))
            print(f"📦 Diretório do experimento movido para: {completed_dir}")


def prepare_environment():
    print("-------------------------------------------------")
    print("Preparando o ambiente...")
    print("-------------------------------------------------")
    verify_environment()


def verify_environment():
    print("-------------------------------------------------")
    print(f"Caminho do ambiente virtual (pyenv): {project_path_pyenv}")
    if project_path_pyenv.exists():
        print(f"Ambiente virtual encontrado: {project_path_pyenv}")
        try:
            subprocess.run(["pyenv", "--version"], check=True, stdout=subprocess.DEVNULL)
            print("Pyenv está instalado e configurado.")
        except subprocess.CalledProcessError:
            print("Erro: pyenv não está instalado ou configurado corretamente.")
    else:
        print(f"Ambiente virtual não encontrado: {project_path_pyenv}")
        create_virtualenv()
        install_dependencies()


def create_virtualenv():
    os.chdir(project_path)
    result = subprocess.run('pyenv virtualenvs --bare', shell=True, capture_output=True, text=True)
    if venv_name not in result.stdout.split():
        print(f"Criando ambiente virtual {venv_name} com Python {python_version}...")
        subprocess.run(f"pyenv virtualenv {python_version} {venv_name}", shell=True, check=True)
    else:
        print(f"Ambiente virtual {venv_name} já existe.")


def activate_virtualenv(command: str) -> str | None:
    try:
        full_cmd = (
            f'bash -c "'
            f'cd \"{project_path}\" && '
            f'eval $(pyenv init --path) && '
            f'eval $(pyenv init -) && '
            f'pyenv activate {venv_name} && '
            f'{command}"'
        )
        print(f"Executando comando no ambiente virtual:\n{full_cmd}")
        result = subprocess.run(full_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout.strip():
            print(f"Saída:\n{result.stdout}")
        if result.stderr.strip():
            print(f"Erros (stderr):\n{result.stderr}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao executar comando no ambiente virtual:\n{e.stderr}")
        return None


def install_dependencies():
    print("🔧 Instalando dependências do projeto...")
    os.chdir(project_path)
    command = (
        'pip install poetry && '
        'poetry install && '
        'pip install -e .'
    )
    activate_virtualenv(command)


def count_real_failures(log_output: str) -> int:
    match = re.search(r"=+.*?([\d]+) failed", log_output, re.IGNORECASE | re.DOTALL)
    if match:
        return int(match.group(1))
    return 0


def run_tests() -> bool:
    print("Executando os testes automatizados com pytest...")
    pytest_command = (
        'pytest -v --cov=. --cov-report=term-missing --cov-report=html --cov-context=test --cache-clear'
    )
    log_output = activate_virtualenv(pytest_command)
    if log_output is None:
        print("❌ Falha ao executar os testes.")
        return False

    generate_logs(log_output)

    failures = count_real_failures(log_output)
    if failures == 0:
        print("✅ Testes concluídos com sucesso.")
        return True
    else:
        print(f"❌ {failures} teste(s) com falha. Abortando execução do SonarQube.")
        return False


def generate_logs(log: str):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        filename=str(log_path),
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info(log)
    print("✅ Logs gerados com sucesso.")
    print(f"Logs salvos em: {log_path}")
    return log


def run_sonarqube(project_key: str, local_project_path: Path, venv_name: str):
    import subprocess

    print("Copiando projeto para a VM...")

    remote_user = "sonarqube"
    remote_host = "192.168.1.7"
    remote_project_path = "/home/sonarqube/projects"
    remote_sonar_path = "/opt/sonar-scanner/bin/sonar-scanner"

    # Copiar conteúdo do projeto para a VM
    scp_copy_cmd = f"scp -r {local_project_path}/* {remote_user}@{remote_host}:{remote_project_path}/"
    subprocess.run(scp_copy_cmd, shell=True, check=True)

    print("Executando análise SonarQube via SSH na VM...")
    # Executar análise SonarQube via SSH na VM dentro da pasta do projeto
    sonar_cmd = (
        f'cd {remote_project_path} && '
        f'{remote_sonar_path} '
        '-Dsonar.projectBaseDir=. '
        '-Dsonar.sources=. '
        f'-Dsonar.host.url={SONAR_URL} '
        f'-Dsonar.login={SONAR_TOKEN} '
        f'-Dsonar.projectKey={project_key} '
        '-Dsonar.python.version=3.11 '
        '-Dsonar.qualitygate.wait=true '
    )
    ssh_cmd = f'ssh {remote_user}@{remote_host} "{sonar_cmd}"'
    result = subprocess.run(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(result.stdout)
    if result.stderr.strip():
        print("Erros na análise SonarQube:")
        print(result.stderr)

    # Puxar issues via API REST
    output_issues_path = local_project_path / "sonar-issues.json"
    get_sonarqube_issues(project_key, SONAR_URL, SONAR_TOKEN, output_issues_path)

    print(f"Issues salvas em: {output_issues_path}")


def get_sonarqube_issues(project_key: str, sonar_url: str, token: str, output_path: Path):
    print("Buscando issues via API REST do SonarQube...")
    headers = {"Authorization": f"Basic {token.encode('ascii').hex()}"}
    # Mas o correto para token é Basic base64(token:), então vamos montar direito:
    import base64
    token_auth = base64.b64encode(f"{token}:".encode()).decode()
    headers = {"Authorization": f"Basic {token_auth}"}

    issues = []
    page = 1
    page_size = 100
    total = None

    while True:
        params = {
            "componentKeys": project_key,
            "ps": page_size,
            "p": page,
            "resolved": "false"
        }
        url = f"{sonar_url}/api/issues/search"
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Erro ao buscar issues: {response.status_code} {response.text}")
            break

        data = response.json()
        issues.extend(data.get("issues", []))

        total = data.get("total", 0)
        fetched = len(issues)

        print(f"Baixadas {fetched} de {total} issues...")

        if fetched >= total:
            break
        page += 1
        time.sleep(1)  # evitar flood na API

    with open(output_path, "w") as f:
        json.dump({"issues": issues}, f, indent=2)


def classify_sonarqube_issues():
    print("Classificando issues detectadas pelo SonarQube...")

    if not sonarqube_output_path.exists():
        print(f"Arquivo de relatório SonarQube não encontrado: {sonarqube_output_path}")
        return

    with open(sonarqube_output_path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Erro ao ler JSON do SonarQube: {e}")
            return

    issues = data.get("issues", [])
    classification_summary = {}

    with open(classification_output_path, "a") as f_out:
        f_out.write(f"\nClassificação de issues:\n")
        for issue in issues:
            rule = issue.get("rule", "unknown")
            severity = issue.get("severity", "UNKNOWN")
            msg = issue.get("message", "")
            f_out.write(f"- [{severity}] {rule}: {msg}\n")
            classification_summary[severity] = classification_summary.get(severity, 0) + 1

        f_out.write("\nResumo das issues:\n")
        for severity, count in classification_summary.items():
            f_out.write(f"{severity}: {count}\n")

    print(f"Classificação concluída. Resultado salvo em: {classification_output_path}")


if __name__ == "__main__":
    print("Inicando o experimento de Refatoração com LLM...")
    print("-------------------------------------------------")
    run_batch_experiments(1)
