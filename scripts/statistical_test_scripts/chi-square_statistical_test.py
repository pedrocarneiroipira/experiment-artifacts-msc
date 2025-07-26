import numpy as np
from scipy.stats import chi2_contingency

# Tabela de contingência: [Casos resolvidos, Casos não resolvidos]
# Ordem dos modelos: Copilot Chat, Llama, DeepSeek, Gemini

# data = np.array([
#     [95, 55],   # Copilot Chat
#     [83, 67],   # Llama
#     [96, 54],   # DeepSeek
#     [97, 53]    # Gemini
# ])

data = np.array([
    [79, 71],   # Copilot Chat
    [66, 84],   # Llama
    [85, 65],   # DeepSeek
    [82, 68]    # Gemini
])


# Teste Qui-Quadrado
chi2, p, dof, expected = chi2_contingency(data)

# Exibe os resultados
print(f'Chi2 = {chi2:.3f}')
print(f'p-valor = {p:.4f}')
print(f'Graus de liberdade = {dof}')
print('\nFrequências esperadas se não houvesse diferença entre os modelos:')
print(expected)



# Interpretação
if p < 0.05:
    print("\nExiste diferença estatisticamente significativa entre os modelos.")
else:
    print("\nNão foi encontrada diferença estatisticamente significativa entre os modelos.")
