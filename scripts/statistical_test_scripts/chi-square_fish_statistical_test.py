import numpy as np
from scipy.stats import chi2_contingency, fisher_exact

# Acertos por modelo: [zero-shot, few-shot]
dados = {
    "Copilot": [79, 95],
    "Llama": [66, 83],
    "DeepSeek": [85, 96],
    "Gemini": [82, 97]
}

TOTAL = 150  # total de métodos avaliados por técnica

print("Análise por modelo:\n")

# Acumuladores para análise geral
acertos_zero = 0
acertos_few = 0

for modelo, (acertos_zs, acertos_fs) in dados.items():
    erros_zs = TOTAL - acertos_zs
    erros_fs = TOTAL - acertos_fs

    tabela = np.array([
        [acertos_zs, erros_zs],  # Zero-shot
        [acertos_fs, erros_fs]   # Few-shot
    ])

    chi2, p_chi2, dof, expected = chi2_contingency(tabela)
    _, p_fisher = fisher_exact(tabela)

    print(f"Modelo: {modelo}")
    print(f"  Tabela: {tabela.tolist()}")
    print(f"  Qui-quadrado: p = {p_chi2:.4f}")
    print(f"  Fisher:        p = {p_fisher:.4f}\n")

    acertos_zero += acertos_zs
    acertos_few += acertos_fs

# Cálculo da análise geral
total_por_técnica = TOTAL * len(dados)
erros_zero = total_por_técnica - acertos_zero
erros_few = total_por_técnica - acertos_few

tabela_geral = np.array([
    [acertos_zero, erros_zero],  # Zero-shot
    [acertos_few, erros_few]     # Few-shot
])

chi2, p_chi2, dof, expected = chi2_contingency(tabela_geral)
_, p_fisher = fisher_exact(tabela_geral)

print("Análise geral (todos os modelos juntos):")
print(f"  Tabela: {tabela_geral.tolist()}")
print(f"  Qui-quadrado: p = {p_chi2:.4f}")
print(f"  Fisher:        p = {p_fisher:.4f}")
