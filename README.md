# proxy-classifier

Herramienta en Python para recolectar, validar y clasificar proxies públicos por nivel de anonimato (transparente/anónimo/elite), usando concurrencia con ThreadPoolExecutor.

## ¿Qué hace?

El script sigue un pipeline de 4 etapas:

1. **Descarga** listas de proxies públicos (HTTP, SOCKS4, SOCKS5) desde repositorios conocidos y APIs de agregadores.
2. **Chequea conectividad** a nivel de socket TCP, para descartar rápido las IPs que ni siquiera responden.
3. **Prueba funcionalidad real**, haciendo un request HTTP/SOCKS de verdad a través de cada proxy vivo.
4. **Clasifica el nivel de anonimato**, comparando los headers que recibe el servidor de destino contra la IP real del usuario.

Cada etapa guarda su resultado en un archivo separado, así podés correr el pipeline por partes sin repetir trabajo.

## Uso

```bash
python3 Listas_Proxy.py
```

El script muestra un menú interactivo:
- **Opción 1**: descarga las listas de fuentes configuradas.
- **Opción 2 → submenú**: procesa las listas descargadas (conectividad → funcionalidad → clasificación).

## Archivos generados

| Archivo | Contenido |
|---|---|
| `01_PROXIES_VIVOS.txt` | Proxies que respondieron al chequeo de socket |
| `02_PROXIES_FUNCIONALES.txt` | Proxies que efectivamente sirvieron una request real |
| `03_PROXIES_CLASIFICADOS.txt` | Proxies con su nivel de anonimato (Transparente/Anónimo/Elite) |

## Decisiones de diseño

- **Test de anonimato sobre HTTP plano (no HTTPS)** para proxies HTTP: así el proxy puede realmente ver y modificar la petición, algo que no pasa con HTTPS + CONNECT, donde el proxy solo túnela sin ver contenido.
- **Concurrencia con `ThreadPoolExecutor`**, separando el número de workers según el tipo de chequeo (más agresivo para sockets, más conservador para requests HTTP reales) por el costo distinto de cada operación.
- **Separación en 3 archivos** en vez de uno solo, para poder re-ejecutar una etapa puntual sin repetir las anteriores.

## Roadmap / mejoras futuras

- [ ] Type hints en todas las funciones
- [ ] Modo no interactivo con `argparse`
- [ ] Reintentos con backoff en descargas fallidas
- [ ] Configuración de fuentes en archivo externo (YAML/JSON)

## Licencia

MIT — ver [LICENSE](LICENSE)
