
# 1. Built-in
import os
import re
import time
import json
import shutil
import logging
import subprocess
from pathlib import Path
from collections import defaultdict

# 2. Third-party
import requests

# Configurações do SonarQube
SONAR_URL = "http://192.168.1.6:9000"
SONAR_TOKEN = "sqa_4db91a7c26b1b14ba7b150f125039e7563ed61fb"  # Use o token gerado no SonarQube

# Caminhos base e variáveis globais
project_path_base = Path("/media/pedrinho/MESTRADO/DISSERTACAO/Experimento_Final/project")
python_version = "3.11.0"
venv_name = "poetry"

# Inicialmente essas variáveis serão atualizadas no loop
project_path = project_path_base / venv_name
project_path_pyenv = Path.home() / ".pyenv" / "versions" / venv_name
log_path = project_path / f'test_{venv_name}.log'
sonarqube_output_path = project_path / f'sonar_{venv_name}.json'
classification_output_path = project_path / f'classification_{venv_name}.txt'


def safe_copytree(src, dst):
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
    except shutil.Error as e:
        print(f"[Aviso] Erros durante a cópia de arquivos: {e}")
    except FileNotFoundError as e:
        print(f"[Aviso] Diretório não encontrado: {e.filename}")


def run_batch_experiments(num_experiments=15):
    import subprocess

# Mata qualquer processo usando a porta UDP 50001 (ignora erro se não houver nenhum)
    subprocess.run("fuser -k 50001/udp", shell=True, stderr=subprocess.DEVNULL)
    base_dir = Path("/media/pedrinho/MESTRADO/DISSERTACAO/Experimento_Final/project")
    
    for i in range(13, num_experiments + 1):
        src_instance = base_dir / f"poetry_{i}"
        working_dir = base_dir / "poetry"
        completed_dir = base_dir / f"poetry_{i}_done"

        print("#################################################################")
        print(f"\n🔁 Iniciando experimento {i}: poetry_{i}")
        print("#################################################################")

        if completed_dir.exists():
            print(f"⚠️ Excluindo {completed_dir} já existente.")
            shutil.rmtree(completed_dir)

        print(src_instance)
        print(working_dir)
        print(f"📁 Copiando {src_instance} para {working_dir}")
        safe_copytree(src_instance, working_dir)
        print(f"📁 Copiado {src_instance} para {working_dir}")

        global project_path, venv_name
        project_path = str(working_dir)
        venv_name = "poetry"

        try:
            run_tests(i)
            classify_sonarqube_issues()

        except Exception as e:
            print(f"❌ Erro no experimento {i}: {e}")

        if working_dir.exists():
            shutil.move(str(working_dir), str(completed_dir))
            print(f"📦 Diretório do experimento movido para: {completed_dir}")



# Ativar o ambiente virtual e executar um comando
def activate_virtualenv(command: str):
    try:
        print(f"Ativando o ambiente virtual '{venv_name}' no diretório '{project_path}'...")

        # Garante que o comando vai ser executado dentro do diretório do projeto
        full_cmd = (
                f'bash -c "'
                f'cd \\"/media/pedrinho/MESTRADO/DISSERTACAO/Experimento_Final/project/poetry\\" && '
                f'eval $(pyenv init --path) && '
                f'eval $(pyenv init -) && '
                f'pyenv activate {venv_name} && '
                f'{command}"'
            )


        print(f"Executando comando:\n{full_cmd}")
        result = subprocess.run(full_cmd,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        return result.stdout, result.stderr

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao ativar ambiente ou executar comando:\n{e.stderr}")
        return None



# Gerar logs dos testes
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


# contagem de falhas reais
def count_real_failures(log_output: str) -> int:
    """
    Conta falhas reais com base em palavras-chave comuns em falhas de execução de testes,
    incluindo falhas de importação, exceções e falhas no próprio pytest.
    """
    error_keywords = [
        "FAILED",            # Testes que falharam
        "ERROR",             # Testes com erro (ex: setup falhou)
        "ImportError",       # Erros de importação
        "ModuleNotFoundError",
        "SyntaxError",
        "Exception",
        "Traceback",         # Em geral indica erro
        "E   ",              # Linha de erro do pytest
        "INTERNALERROR",     # Erros do pytest em si
    ]

    for keyword in error_keywords:
        if keyword in log_output:
            return 1  # Se encontrar qualquer palavra-chave, assume falha

    return 0  # Nenhum erro detectado



# Rodar os testes automatizados
def run_tests(experiment_number):
    print("-----------------------------------------------------------------")
    print("🧪 Executando os testes automatizados...")
    print("-----------------------------------------------------------------")

    try:
        output = (
            'pytest -v --cov=. --cov-report=term-missing --cov-report=html --cov-context=test --cache-clear'
        )
        log_output, log_stderr = activate_virtualenv(output)

        fatal_keywords = [
            "importerror", "modulenotfounderror", "syntaxerror"
        ]
        combined_logs = (log_output + log_stderr).lower()
        fatal_errors = any(keyword in combined_logs for keyword in fatal_keywords)

        print(f"Fatal error: {fatal_errors}")

        log_path = Path("logs") / f"experiment_{experiment_number}_log.txt"

        if fatal_errors:
            generate_logs(log_output + "\n" + log_stderr)
            print("❌ Erro crítico durante a execução dos testes (importação ou sintaxe).")
            with open(log_path, 'a') as log_file:
                log_file.write("\n[ERRO CRÍTICO - TESTES NÃO EXECUTADOS]\n")
                log_file.write(log_output + "\n" + log_stderr)
            return False

        failures = count_real_failures(log_output)

        if failures == 0:
            generate_logs(log_output + "\n" + log_stderr)
            print("✅ Testes concluídos com sucesso.")
            run_sonarqube(f"poetry_{experiment_number}", Path(project_path), venv_name)
            return True
        else:
            generate_logs(log_output + "\n" + log_stderr)
            print(f"❌ {failures} teste(s) com falha real detectado(s). Abortando execução do SonarQube.")
            return False

    except Exception as e:
        print(f"⚠️ Erro ao executar os testes: {e}")
        return False

# deleta um projeto do SonarQube, se existir
def delete_sonarqube_project(project_key: str, sonar_url: str, sonar_token: str):
    import requests

    print(f"Excluindo projeto '{project_key}' do SonarQube (se existir)...")
    response = requests.post(
        f"{sonar_url}/api/projects/delete",
        auth=(sonar_token, ""),
        data={"project": project_key}
    )

    if response.status_code == 204:
        print(f"✅ Projeto '{project_key}' excluído com sucesso.")
    elif response.status_code == 404:
        print(f"ℹ️ Projeto '{project_key}' não encontrado. Nada para excluir.")
    else:
        print(f"⚠️ Erro ao excluir projeto: {response.status_code} - {response.text}")


# roda a análise do SonarQube
def run_sonarqube(project_key: str, local_project_path: Path, venv_name: str):
    import subprocess

    print('---------------------------------------------------')

    # Excluir projeto existente no SonarQube
    # delete_sonarqube_project(project_key, SONAR_URL, SONAR_TOKEN)


    print('---------------------------------------------------')
    print("Copiando projeto para a VM...")

    remote_user = "sonarqube"
    remote_host = "192.168.1.6"
    remote_project_path = "/home/sonarqube/projects"
    remote_sonar_path = "/opt/sonar-scanner/bin/sonar-scanner"

    # Copiar conteúdo do projeto para a VM
    scp_exclude_tests_cmd = (
        f"tar --exclude='tests' --exclude='test' --exclude='htmlcov' "
        f"-czf - -C '{local_project_path}' . | "
        f"ssh {remote_user}@{remote_host} "
        f"'rm -rf \"{remote_project_path}\"/* && tar -xzf - -C \"{remote_project_path}\"'"
    )



    # Executa o comando
    subprocess.run(scp_exclude_tests_cmd, shell=True, check=True)

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
        '-Dsonar.qualitygate.wait=true '
    )
    ssh_cmd = f'ssh {remote_user}@{remote_host} "{sonar_cmd}"'
    result = subprocess.run(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(result.stdout)
    if result.stderr.strip():
        print("Erros na análise SonarQube:")
        print(result.stderr)

    # Puxar issues via API REST
    output_issues_path = local_project_path / f"sonar_{venv_name}.json"
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
    print("Classificando issues de manutenibilidade detectadas pelo SonarQube...")

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
        f_out.write(f"\nClassificação de issues de manutenibilidade:\n")
        for issue in issues:
            component = issue.get("component", "")
            rule = issue.get("rule", "unknown")
            severity_raw = issue.get("severity", "UNKNOWN")
            severity_map = {
                "BLOCKER": "H",
                "CRITICAL": "H",
                "MAJOR": "M",
                "MINOR": "L",
                "INFO": "L"
            }
            severity = severity_map.get(severity_raw, "U")  # U = desconhecida
            msg = issue.get("message", "")
            issue_type = issue.get("type", "UNKNOWN")

            # Filtro 1: Apenas arquivos Python
            if not component.endswith(".py"):
                continue

            # Filtro 2: Apenas problemas de manutenibilidade (code smells)
            if issue_type != "CODE_SMELL":
                continue

            f_out.write(f"- [{severity}] {rule}: {msg}\n")
            classification_summary[severity] = classification_summary.get(severity, 0) + 1

        f_out.write("H: High | M: Medium | L: Low\n")
        for severity in ["H", "M", "L", "U"]:
            count = classification_summary.get(severity, 0)
            f_out.write(f"{severity}: {count}\n")

    print(f"Classificação concluída. Resultado salvo em: {classification_output_path}")



# função principal
if __name__ == "__main__":
    print("Inicando o experimento de Refatoração com LLM...")
    print("-------------------------------------------------")
    run_batch_experiments(13)
    print("-------------------------------------------------")
    print("Experimento concluído.")
    print("Resultados salvos nos arquivos de log e classificação.")
    print("-------------------------------------------------")







