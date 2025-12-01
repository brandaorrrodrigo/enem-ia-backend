
# ENEM-IA • Camada 4 – IA Integrada (Explicação + Plano de Estudos)

## Como rodar
1) Instale dependências (opcional se já tiver ambiente):
   pip install -r requirements.txt

2) Rode o servidor:
   uvicorn main:app --reload --host 0.0.0.0 --port 8001

3) Teste endpoints:
   - POST http://localhost:8001/ia/explicacao
   - POST http://localhost:8001/ia/explicacao/feedback
   - POST http://localhost:8001/ia/plano

## Exemplo de body: /ia/explicacao

{
  "questao_id": 123,
  "enunciado": "Um móvel parte do repouso...",
  "alternativas": {"A": "10 m", "B": "20 m", "C": "30 m", "D": "40 m", "E": "50 m"},
  "resposta_usuario": 1,
  "correta": 3,
  "usuario": "Rodrigo"
}

Resposta traz `session_id` para continuar a conversa em /ia/explicacao/feedback.

## Exemplo de body: /ia/explicacao/feedback

{
  "session_id": "<copie_da_resposta_anterior>",
  "entendeu": false,
  "usuario": "Rodrigo"
}

Se `entendeu=false`, o sistema simplifica a explicação (nível 2, 3, 4).

## Exemplo de body: /ia/plano

{
  "usuario": "Rodrigo",
  "horas_por_dia": 2,
  "objetivo": "ENEM 2025",
  "forcas": ["humanas"],
  "fraquezas": ["fisica", "matematica"],
  "historico": []
}

