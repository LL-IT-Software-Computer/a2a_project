# Fonctionnement des scripts A2A

Ce document décrit comment interagissent les deux scripts Python :

| Script | Rôle | Point d’entrée |
|--------|------|----------------|
| **`a2a_example.py`** | Serveur : expose un agent A2A nommé *Echo+ Agent* capable d’appliquer plusieurs styles au texte (MAJUSCULES, minuscules, *snake_case*, …). | `uvicorn a2a_example:app …` |
| **`a2a_llm_agent.py`** | Serveur : proxy vers l’API OpenAI avec résumé de documents. | `uvicorn a2a_llm_agent:app …` |
| **`test_python.py`** | Client : découvre la carte A2A de l’agent, envoie un message une première fois en mode *non‑streaming*, puis refait la même requête en mode *streaming* SSE. | `python3 test_python.py` |

---

## 1. Schéma général

```mermaid
sequenceDiagram
    participant Client
    participant AgentServer as Echo+ Agent

    Client->>AgentServer: GET /.well‑known/agent.json (carte A2A)
    AgentServer-->>Client: AgentCard (JSON)

    Client->>AgentServer: JSON‑RPC message/send ("salut")
    AgentServer-->>Client: Réponse "SALUT" (non‑stream)

    Client->>AgentServer: JSON‑RPC message/stream ("salut")
    AgentServer-->>Client: flux SSE "SALUT\n" (chunks)
```

---

## 2. Détails de `a2a_example.py`

### 2.1 EchoAgent
```python
class EchoAgent:
    async def transform(self, text: str, style: str) -> str:
        await asyncio.sleep(0.1)  # petite latence simulée
        if style == "uppercase":
            return text.upper()
        if style == "lowercase":
            return text.lower()
        if style == "snake_case":
            return text.replace(" ", "_").lower()
        return text
```
*Applique simplement le style demandé au texte reçu.*

### 2.2 EchoAgentExecutor
* Pont entre le protocole A2A et la logique métier.
* Récupère le message utilisateur via `RequestContext` → `params.message`.
* Extrait puis concatène les parties texte (`parts`).
* Appelle `EchoAgent.transform` avec le style choisi.
* Empile la réponse dans `event_queue` (obligatoirement avec `await`).

### 2.3 AgentCard  
Expose publiquement, à l’URL `http://localhost:9999/.well-known/agent.json`, une **fiche d’identité** décrivant :
* nom, description, version,
* compétences (skill *echo-plus*),
* indicateur `capabilities.streaming = true` (support SSE).

### 2.4 Application Starlette  
Le serveur est construit avec :  

```python
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build()
```
Il suffit donc de lancer :

```bash
uvicorn a2a_example:app --host 0.0.0.0 --port 9999 --reload
```

---

## 3. Détails de `test_python.py`

| Étape | Explication |
|-------|-------------|
| **1.** `A2ACardResolver.get_agent_card()` | Télécharge la carte JSON pour récupérer l’URL, les capabilities, etc. |
| **2.** Instanciation d’`A2AClient` | Fournit le `agent_card` + le client HTTPX partagé. |
| **3.** **Non‑streaming** (`send_message`) | Envoie un objet `SendMessageRequest` → reçoit un `Message` complet. |
| **4.** **Streaming** (`send_message_streaming`) | Envoie la même requête via `SendStreamingMessageRequest` → itère sur les « chunks » SSE (chaque chunk est un `Message` ou un événement de contrôle). |

### 3.1 Payload minimal

```python
payload = {
    "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "salut"}],
        "messageId": uuid4().hex
    }
}
```

Le wrapper `MessageSendParams(**payload)` sérialise tout selon le schéma A2A.

---

## 4. Exécution pas‑à‑pas

```bash
# 1) Démarrer l’agent
uvicorn a2a_example:app --host 0.0.0.0 --port 9999 --reload

# 2) Dans un autre terminal, lancer le client
python3 test_python.py
```

Sortie attendue :

```
Réponse non‑streaming : … 'text': 'SALUT' …
Chunk streaming       : … 'text': 'SALUT' …
```

### 4.1 Proxy LLM et résumé de documents

Pour tester l'autre serveur, définissez d'abord la clé OpenAI :

```bash
export OPENAI_API_KEY=...  # votre clé API
```

Puis lancez :

```bash
uvicorn a2a_llm_agent:app --host 0.0.0.0 --port 9999 --reload
```

Vous pouvez réutiliser `test_python.py` ou simplement appeler l'API :

```bash
curl -X POST http://localhost:9999/ \
  -H 'Content-Type: application/json' \
  -d '{"message": {"role": "user", "parts": [{"kind": "text", "text": "Bonjour"}]}}'
```

---

## 5. Personnalisation

* **Transformer autre chose que du texte** : ajouter des `input_modes` (ex. `image`) et étendre `transform`.
* **Réponses plus longues / incrémentales** : diviser `transformed` en plusieurs messages et les `await event_queue.enqueue_event(msg)` un par un.
* **Sécurité / Auth** : définir `supports_authenticated_extended_card=True` et protéger l’endpoint via un *middleware* Starlette.

---

## 6. Dépendances minimales

```txt
a2a-python>=0.5
httpx>=0.26
httpx-sse>=0.4
uvicorn[standard]>=0.29
openai>=1.0
```

L’API OpenAI nécessite la variable d’environnement `OPENAI_API_KEY`.

Verrouille la version du SDK pour éviter de futures ruptures :

```txt
a2a-python==0.5.3
```

## Installation

Installez les dépendances dans un environnement virtuel :

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

_Fin du document._  
