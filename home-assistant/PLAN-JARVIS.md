# Plan: Jarvis más inteligente (modelo de lenguaje local)

Estado: **sin aplicar.** Este archivo junta las opciones y los pasos para cuando se decida.

## Para qué

Hoy Jarvis usa el agente de HA, que solo entiende frases fijas. En la prueba del 2026-10-19 funcionaron
"What time is it?", "Turn off all the lights" y "Set the bedroom lights at 20%", pero fallaron
variaciones como "Turn on the lights", "Set the brightness at 10%" y "Set all the lights brightness
at 10%".

Lo que se busca:

- **Que recuerde las últimas frases** (unas 3). Por ejemplo, "prendé la luz" y después "bajala al 10%".
- **Que deduzca mejor** lo que se le pide aunque la frase no sea exacta.
- **Más adelante:** que tome notas y que ponga canciones.

## Lo que ya está hecho

| Pieza | Estado |
|---|---|
| Whisper (voz → texto) | Contenedor `whisper` en la GPU (`medium-int8`), integración Wyoming en HA (`stt.faster_whisper`). Tarda ~0,3 s |
| Piper (texto → voz) | Contenedor `piper`, integración Wyoming (`tts.piper`). Voces: `es_AR-daniela-high` y `en_GB-alan-medium` |
| Asistente **Jarvis** (predeterminado) | Inglés: Whisper `en` → agente de HA `en` → Piper `en_GB-alan-medium`. `prefer_local_intents: true` |
| Asistente **Voz local (español)** | Español: Whisper `es` → agente de HA `es` → Piper `es_AR-daniela-high` |
| Luces para el asistente | `light.room` y las 3 CLA60 expuestas y en el área Bedroom. La pantalla del kiosco no está expuesta |
| Áreas | Alias en español: dormitorio/pieza/cuarto/habitación, living/sala/comedor, cocina |
| Palabra de activación | **Falta.** Ver "Pendiente aparte" |

Los asistentes, integraciones, alias y entidades expuestas los guarda HA en `.storage`, no este repo.

## Recursos y conflicto con job-autoapply

- La GPU (RTX 2060 Super) tiene **8 GB**. Whisper ocupa **1,7 GB** de forma fija.
- **job-autoapply** tiene su propio Ollama con **qwen3:8b** (5,2 GB). Lo carga al terminar cada corrida
  para redactar borradores y lo descarga al terminar (`keep_alive` 2m, después 0). Fuera de eso no
  ocupa la placa.
- Si Jarvis usa un modelo grande, los dos no entran a la vez. Ollama no se cae: manda parte del
  modelo a la RAM y responde varias veces más lento. Para los borradores de job-autoapply, que corren
  en segundo plano, da igual. Para Jarvis no.
- **Frigate** (apagado por ahora) también usa la GPU. Si se vuelve a prender, hay que recalcular.
- Ollama vuelve a cargar el modelo si dos clientes lo piden con distinto `num_ctx`. Por eso no
  conviene compartir la misma instancia de Ollama con job-autoapply: además, este descarga el modelo
  al terminar (`keep_alive: 0`) y se lo sacaría a Jarvis.

## Opciones de modelo

| Modelo para Jarvis | En la placa | Junto con job-autoapply (qwen3:8b) | Calidad para esto |
|---|---|---|---|
| qwen3:8b | ~5,2 GB | No entra: alguno se pone lento | La mejor. Deduce bien y se equivoca poco con las herramientas |
| **qwen3:4b** (recomendado) | ~3 GB | Casi: se derrama un poco a la RAM solo mientras corre job-autoapply | Muy parecida a 8b (37 vs 38 en el bench de job-autoapply, `Job-autoapply/docs/PLAN-modelo-local.md`). Alcanza para deducir, recordar, notas y música |
| qwen3:1.7b | ~1,5 GB | Sí, sobra lugar | Se nota peor: se confunde con las herramientas e inventa más |
| Claude por API | 0 | Sin conflicto | La mejor y entiende español aunque conteste en inglés. Se paga por uso, necesita internet y el pedido sale de la casa |

### Costos de qwen3:4b siempre cargado

| Recurso | Costo |
|---|---|
| Memoria de la GPU | ~3,5 GB fijos (modelo + contexto). Con Whisper: ~5,2 de 8 GB |
| Disco | ~2,5 GB del modelo + ~3–4 GB de la imagen de Ollama (la misma que usa job-autoapply) |
| RAM | ~0,5–1 GB |
| CPU | Casi nada |
| Electricidad | En reposo casi igual. Mientras responde, la placa trabaja a full 1–2 s |
| Velocidad | Los comandos que HA entiende solo siguen siendo instantáneos. El resto tarda ~1–2 s más |

Variante para ahorrar placa: en vez de dejarlo siempre cargado, descargarlo después de 10 minutos sin
uso. En reposo no ocupa nada, pero la primera pregunta después de eso tarda ~5–15 s más mientras carga.

## Plan (con qwen3:4b)

1. **Ollama propio para HA** en `docker-compose.yml`. Va en la red `home` y no publica puerto a la LAN.

   ```yaml
   ollama:
     container_name: ollama
     image: ollama/ollama:latest
     networks:
       - home
     environment:
       OLLAMA_KEEP_ALIVE: "-1" # siempre cargado; "10m" para la variante que ahorra placa
     volumes:
       - ollama_data:/root/.ollama
     restart: unless-stopped
     deploy:
       resources:
         limits:
           cpus: "4"
           memory: 4G
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
   ```

   Y en `volumes:` sumar `ollama_data:`. Después: `docker compose up -d ollama` y
   `docker exec ollama ollama pull qwen3:4b`.

2. **Integración Ollama en HA:** URL `http://ollama:11434` y un agente de conversación con:
   - modelo `qwen3:4b`, sin razonamiento ("think" apagado: gasta tiempo y en voz no sirve),
   - control de la casa con la API **Assist** de HA,
   - contexto de 8192 tokens (alcanza con las pocas entidades expuestas y el historial),
   - instrucciones de personalidad: mayordomo británico, respuestas cortas en inglés, sin markdown
     ni emojis porque se leen en voz alta.
3. **Asistente Jarvis:** cambiar el agente de conversación al de Ollama y dejar
   `prefer_local_intents: true`. Así los comandos exactos no pasan por el modelo.
4. **Notas:** crear una lista de tareas local "Notes" (integración Local To-do) y exponerla. Frases:
   "add a note: buy coffee", "what's on my notes?".
5. **Verificar:**
   - las frases que fallaron en la prueba del 2026-10-19,
   - memoria: "turn on the bedroom lights" y después "dim them to 10%",
   - `nvidia-smi` con Jarvis cargado y durante una corrida de job-autoapply,
   - tiempos por pedido en Configuración → Asistentes de voz → Jarvis → Depurar.

## Más adelante

- **Poner canciones:** HA no sabe buscar música en Haze por su cuenta. Hay que armar un script
  expuesto al asistente (por ejemplo `script.jarvis_play_song` con un campo `query`) que le pase
  el pedido a Haze. Falta ver qué acepta Haze para buscar y reproducir.
- **Hablar en español y que conteste en inglés:** solo con un modelo de lenguaje. El agente de HA
  siempre contesta en el idioma en que se le habla.

## Pendiente aparte: palabra de activación "Hey Jarvis"

- openWakeWord trae **"hey jarvis"** listo. "Jarvis" solo habría que entrenarlo aparte y da más
  falsos positivos.
- Hace falta openWakeWord en el servidor (contenedor Wyoming) y un programa que escuche el micrófono
  todo el tiempo y le mande el audio a HA, en el equipo donde esté el micrófono:
  - **Pi del kiosco (MRTN-HUB):** lo más simple y queda siempre escuchando. Necesita un micrófono USB.
  - **PC con Windows:** el programa de Wyoming está pensado para Linux. En Windows anda, pero con más
    vueltas.
- Desde el navegador no hay palabra de activación: solo funciona apretando el micrófono, y en `http`
  hay que habilitar el sitio en `chrome://flags/#unsafely-treat-insecure-origin-as-secure`.
