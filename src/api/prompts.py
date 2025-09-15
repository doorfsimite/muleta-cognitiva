"""Prompt templates for LLM entity and relation extraction."""


def build_extraction_prompt(text: str, source_type: str) -> str:
    """Build extraction prompt for LLM.

    Args:
        text: Input text to process
        source_type: Type of source (text, pdf, video)

    Returns:
        Formatted prompt string
    """
    return f"""Tarefa:
Você receberá um texto-fonte. Sua missão é ajudar a aprender o conteúdo identificando entidades e relações entre elas, para construir um grafo de conhecimento (como uma wiki) e servir de base para um infográfico.

Regras gerais:
- Use apenas informações presentes no texto fornecido (sem conhecimento externo).
- Escreva todas as descrições em português do Brasil.
- Seja objetivo e evite parábolas.
- Normalize nomes de entidades (forma canônica, singular quando apropriado).
- Se houver entidades duplicadas, consolide em um único nome canônico.
- Se não tiver certeza do tipo de relação, use "relacionado_a".
- Se não encontrar nada relevante, retorne "entities": [] e "relations": [].
- Responda APENAS com JSON válido, sem comentários, sem texto fora do JSON.
- Desconsidere texto mal formatado. O input pode ter sido dinamicamente gerado a partir de audio ou imagem e pode ter ruido.

Entrada:
- Um único bloco de texto.

Passos de análise (internos):
1) Leia e segmente o texto em parágrafos/tópicos.
2) Liste candidatos a entidades: conceitos, pessoas, lugares, organizações, obras, eventos, tecnologias, métodos, problemas, soluções, premissas, conclusões, temas/assuntos.
3) Selecione as entidades essenciais ao entendimento do texto (evite termos triviais).
4) Para cada entidade selecionada, gere:
   - name: nome canônico curto e claro.
   - type: um dos tipos permitidos (ver abaixo).
   - description: resumo objetivo do papel/definição no contexto do texto.
5) Identifique relações explícitas ou fortemente implícitas entre as entidades.
6) Para cada relação, registre:
   - from, to: nomes canônicos das entidades.
   - type: um dos tipos permitidos (ver abaixo).
   - evidence: citação curta do texto OU explicação breve baseada no texto.
7) Valide o JSON: chaves corretas, aspas duplas, sem vírgulas sobrando.

Formato de saída (JSON):
{{
  "entities": [
    {{
      "name": "Nome da Entidade", 
      "type": "tipo", 
      "description": "descrição em PT-BR com até 25 palavras"
    }}
  ],
  "relations": [
    {{
      "from": "Entidade1", 
      "to": "Entidade2", 
      "type": "tipo_relacao", 
      "evidence": "Citação curta do texto ou explicação objetiva baseada no texto"
    }}
  ]
}}

Exemplo (apenas demonstrativo):
{{
  "entities": [
    {{
      "name": "Aprendizado Baseado em Grafos", 
      "type": "conceito", 
      "description": "Estratégia que organiza conhecimento como nós e arestas para facilitar entendimento e revisão."
    }},
    {{
      "name": "Entidade", 
      "type": "conceito", 
      "description": "Elemento fundamental do grafo representando um conceito, pessoa, lugar, evento ou objeto."
    }},
    {{
      "name": "Relação", 
      "type": "conceito", 
      "description": "Ligação semântica entre entidades que expressa dependência, causalidade, composição ou associação."
    }}
  ],
  "relations": [
    {{
      "from": "Aprendizado Baseado em Grafos", 
      "to": "Entidade", 
      "type": "parte_de", 
      "evidence": "O método define entidades e relações como componentes do grafo."
    }},
    {{
      "from": "Aprendizado Baseado em Grafos", 
      "to": "Relação", 
      "type": "parte_de", 
      "evidence": "A abordagem usa relações para conectar conceitos no grafo."
    }},
    {{
      "from": "Entidade", 
      "to": "Relação", 
      "type": "relacionado_a", 
      "evidence": "As entidades são conectadas por relações."
    }}
  ]
}}

TEXTO ({source_type}):
{text}"""
