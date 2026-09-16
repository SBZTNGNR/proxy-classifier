import requests
import socket
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

gris = "\033[90m"
rojo_brillante = "\033[91m"
verde_brillante = "\033[92m"
amarillo_brillante = "\033[93m"
azul_brillante = "\033[94m"
magenta_brillante = "\033[95m"
cian_brillante = "\033[96m"
blanco_brillante = "\033[97m"
reset = "\033[0m"

ruta_base = Path.home() / "Documentos" / "Proxy Lists"
servidores_ok = []
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; ProxyChecker/1.0)"}
URL_PRUEBA = "https://httpbin.org/ip"
URL_HEADERS_HTTP = "http://httpbin.org/get"
URL_HEADERS_HTTPS = "https://httpbin.org/get"
HEADERS_PROXY_CONOCIDOS = ["Via", "X-Forwarded-For", "Forwarded", "X-Real-Ip", "Proxy-Connection", "X-Proxy-Id"]

MAX_WORKERS_SOCKET = 100
MAX_WORKERS_HTTP = 50


def generar_nombre_archivo(categoria, url):
	partes = urlparse(url)
	dominio = partes.netloc.replace("www.", "")
	
	ruta_limpia = partes.path.strip("/").replace("/", "_")
	if not ruta_limpia:
		ruta_limpia = "lista.txt"
	if not ruta_limpia.endswith(".txt"):
		ruta_limpia += ".txt"
	return f"{categoria}_{dominio}_{ruta_limpia}"


def cargar_lista():
	lista_proxy = {"HTTP": ["https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
							"https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
							"https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"],
					"SOCKS5": ["https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
							"https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
							"https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt"],
					"SOCKS4": ["https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
							"https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt"],
					"API_HTTP": ["https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all"],
					"API_SOCKS5": ["https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all"]}
	
	print(f"{verde_brillante}-Cargando Listas de Inicialización-\n{reset}")
	for categorias, urls in lista_proxy.items():
		for z in urls:
			try:
				respuesta = requests.head(z, headers=CABECERAS, timeout=3, allow_redirects=True)
				if respuesta.status_code == 200:
					print(f"{verde_brillante}Conectividad OK (200):{reset} {amarillo_brillante}{z}{reset}")
					servidores_ok.append((categorias, z))
				else:
					print(f"{rojo_brillante}Servidor responde pero con código:{reset}{gris} {respuesta.status_code}:{reset} {amarillo_brillante}{z}{reset}")
			
			except requests.exceptions.Timeout:
				print(f"{rojo_brillante}Tiempo de espera agotado (Timeout): {z}{reset}")
			except requests.exceptions.RequestException:
				print(f"{rojo_brillante}Error de red / No existe el dominio: {z}{reset}")


def descargar_archivos():
	ruta_base.mkdir(parents=True, exist_ok=True)
	for categoria, x in servidores_ok:
		try:
			proxy_list = requests.get(x, headers=CABECERAS, timeout=15)
			proxy_list.raise_for_status()
			
			content_length = proxy_list.headers.get("Content-Length")
			codificado = proxy_list.headers.get("Content-Encoding")
			
			if content_length and not codificado and int(content_length) != len(proxy_list.content):
				print(f"{rojo_brillante}[!] Advertencia: la descarga podría estar incompleta:{reset} {x}")
				
			if not proxy_list.text.strip():
				print(f"{rojo_brillante}[!] Advertencia: el archivo llegó vacío:{reset} {x}")
				
			nombre_archivo = generar_nombre_archivo(categoria, x)
			ruta_archivo = ruta_base / nombre_archivo
			
			with open(ruta_archivo, "w", encoding="UTF-8") as archivo:
				archivo.write(proxy_list.text)
				print(f"[+] Guardado correctamente: {nombre_archivo} ({len(proxy_list.content)} bytes)")
		except requests.exceptions.RequestException as e:
			print(f"[!] Error al descargar desde: {x} ({e})")
		except OSError:
			print("[!] Error en la ruta del archivo")


def extraer_categoria(nombre_archivo):
	if nombre_archivo.startswith("API_"):
		return "_".join(nombre_archivo.split("_")[:2])
	return nombre_archivo.split("_")[0]


def probar_conexion(ip, puerto, timeout=3):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(timeout)
	try:
		resultado = sock.connect_ex((ip, puerto))
		return resultado == 0
	except (socket.timeout, socket.error):
		return False
	finally:
		sock.close()


def recolectar_proxies():
	proxies_unicos = set()
	lista_carpeta = list(ruta_base.glob("*.txt"))
	
	for archivo in lista_carpeta:
		if archivo.name in ("01_PROXIES_VIVOS.txt", "02_PROXIES_FUNCIONALES.txt", "03_PROXIES_CLASIFICADOS.txt"):
			continue
		
		categoria = extraer_categoria(archivo.name)
		
		try:
			contenido = archivo.read_text(encoding="UTF-8")
		except UnicodeDecodeError:
			print(f"{rojo_brillante}[!] No se pudo leer: {archivo.name}{reset}")
			continue
		
		for linea in contenido.splitlines():
			linea = linea.strip()
			partes = linea.split(":")
			if len(partes) == 2 and partes[1].isdigit():
				ip, puerto = partes[0], int(partes[1])
				proxies_unicos.add((categoria, ip, puerto))
	
	proxies_a_probar = list(proxies_unicos)
	print(f"{verde_brillante}Total de proxies únicos a probar: {len(proxies_a_probar)}{reset}")
	return proxies_a_probar


def chequear_conectividad():
	if not ruta_base.exists():
		print("No existe la ruta de los archivos.")
		return
	
	proxies_a_probar = recolectar_proxies()
	proxies_vivos_por_categoria = {}
	total_vivos = 0
	total = len(proxies_a_probar)
	
	print(f"{verde_brillante}Probando conectividad con {MAX_WORKERS_SOCKET} en paralelo:{reset}")
	
	with ThreadPoolExecutor(max_workers=MAX_WORKERS_SOCKET) as executor:
		futuros = {
			executor.submit(probar_conexion, ip, puerto): (categoria, ip, puerto)
			for categoria, ip, puerto in proxies_a_probar
		}
		
		completados = 0
		for futuro in as_completed(futuros):
			categoria, ip, puerto = futuros[futuro]
			completados += 1
			
			if futuro.result():
				proxies_vivos_por_categoria.setdefault(categoria, []).append((ip, puerto))
				total_vivos += 1
			
			if completados % 200 == 0 or completados == total:
				print(f"{gris}Progreso: {completados}/{total} ({total_vivos} vivos hasta ahora){reset}")
	
	print(f"\n{verde_brillante}Proxies vivos: {total_vivos} de {total}{reset}")
	
	ruta_vivos = ruta_base / "01_PROXIES_VIVOS.txt"
	with open(ruta_vivos, "w", encoding="UTF-8") as archivo:
		for categoria, lista_ips in proxies_vivos_por_categoria.items():
			archivo.write(f"# {categoria}\n")
			for ip, puerto in sorted(lista_ips):
				archivo.write(f"{ip}:{puerto}\n")
	print(f"{verde_brillante}[+] Guardado en:{reset} {ruta_vivos}")
	
	return proxies_vivos_por_categoria


def cargar_lista_desde_archivo(nombre_archivo):
	ruta_archivo = ruta_base / nombre_archivo
	if not ruta_archivo.exists():
		print(f"{rojo_brillante}[!] No existe {nombre_archivo}.{reset}")
		return []
	
	proxies = []
	categoria_actual = None
	for linea in ruta_archivo.read_text(encoding="UTF-8").splitlines():
		linea = linea.strip()
		if not linea:
			continue
		if linea.startswith("#"):
			categoria_actual = linea.lstrip("#").strip()
		else:
			ip, puerto = linea.split(":")
			proxies.append((categoria_actual, ip, int(puerto)))
	return proxies


def armar_url_proxy(categoria, ip, puerto):
	if "SOCKS5" in categoria:
		return f"socks5://{ip}:{puerto}"
	elif "SOCKS4" in categoria:
		return f"socks4://{ip}:{puerto}"
	else:
		return f"http://{ip}:{puerto}"


def probar_proxy_funcional(categoria, ip, puerto, timeout=5):
	proxy_url = armar_url_proxy(categoria, ip, puerto)
	proxies = {"http": proxy_url, "https": proxy_url}
	
	try:
		respuesta = requests.get(URL_PRUEBA, proxies=proxies, timeout=timeout)
		return respuesta.status_code == 200
	except requests.exceptions.RequestException:
		return False


def probar_funcionalidad():
	proxies_vivos = cargar_lista_desde_archivo("01_PROXIES_VIVOS.txt")
	if not proxies_vivos:
		return
	
	total = len(proxies_vivos)
	print(f"{verde_brillante}Probando funcionalidad real de {total} proxies con {MAX_WORKERS_HTTP} en paralelo:{reset}")
	proxies_funcionales = []
	completados = 0
	
	with ThreadPoolExecutor(max_workers=MAX_WORKERS_HTTP) as executor:
		futuros = {
			executor.submit(probar_proxy_funcional, categoria, ip, puerto): (categoria, ip, puerto)
			for categoria, ip, puerto in proxies_vivos
		}
		
		for futuro in as_completed(futuros):
			categoria, ip, puerto = futuros[futuro]
			completados += 1
			
			if futuro.result():
				proxies_funcionales.append((categoria, ip, puerto))
			
			if completados % 100 == 0 or completados == total:
				print(f"{gris}Progreso: {completados}/{total} ({len(proxies_funcionales)} funcionales hasta ahora){reset}")
	
	print(f"\n{verde_brillante}Proxies funcionales: {len(proxies_funcionales)} de {total}{reset}")
	
	ruta_funcionales = ruta_base / "02_PROXIES_FUNCIONALES.txt"
	with open(ruta_funcionales, "w", encoding="UTF-8") as archivo:
		categoria_previa = None
		for categoria, ip, puerto in sorted(proxies_funcionales):
			if categoria != categoria_previa:
				archivo.write(f"# {categoria}\n")
				categoria_previa = categoria
			archivo.write(f"{ip}:{puerto}\n")
	print(f"{verde_brillante}[+] Guardado en:{reset} {ruta_funcionales}")
	
	return proxies_funcionales


def obtener_ip_real():
	try:
		respuesta = requests.get(URL_PRUEBA, timeout=5)
		return respuesta.json().get("origin", "").split(",")[0].strip()
	except requests.exceptions.RequestException:
		return None

def clasificar_anonimato(categoria, ip, puerto, ip_real, timeout=5):
	proxy_url = armar_url_proxy(categoria, ip, puerto)
	proxies = {"http": proxy_url, "https": proxy_url}
	
	# Para proxies HTTP, probamos contra HTTP plano, así el proxy puede
	# realmente ver y modificar la petición (a diferencia de HTTPS con CONNECT)
	if "SOCKS" in categoria:
		url_prueba = URL_HEADERS_HTTPS
	else:
		url_prueba = URL_HEADERS_HTTP
	
	try:
		respuesta = requests.get(url_prueba, proxies=proxies, timeout=timeout)
		if respuesta.status_code != 200:
			return None
		
		headers_recibidos = respuesta.json().get("headers", {})
		texto_headers = " ".join(str(v) for v in headers_recibidos.values())
		
		if ip_real and ip_real in texto_headers:
			return "Transparente"
		
		if any(h in headers_recibidos for h in HEADERS_PROXY_CONOCIDOS):
			return "Anonimo"
		
		return "Elite"
	except requests.exceptions.RequestException:
		return None


def clasificar_proxies():
	proxies_funcionales = cargar_lista_desde_archivo("02_PROXIES_FUNCIONALES.txt")
	if not proxies_funcionales:
		return
	
	print(f"{verde_brillante}Obteniendo IP real para comparación...{reset}")
	ip_real = obtener_ip_real()
	if not ip_real:
		print(f"{rojo_brillante}[!] No se pudo obtener la IP real. Abortando.{reset}")
		return
	print(f"{verde_brillante}IP real detectada: {ip_real}{reset}\n")
	
	total = len(proxies_funcionales)
	print(f"{verde_brillante}Clasificando anonimato de {total} proxies con {MAX_WORKERS_HTTP} en paralelo:{reset}")
	proxies_clasificados = []
	completados = 0
	
	with ThreadPoolExecutor(max_workers=MAX_WORKERS_HTTP) as executor:
		futuros = {
			executor.submit(clasificar_anonimato, categoria, ip, puerto, ip_real): (categoria, ip, puerto)
			for categoria, ip, puerto in proxies_funcionales
		}
		
		for futuro in as_completed(futuros):
			categoria, ip, puerto = futuros[futuro]
			completados += 1
			nivel = futuro.result()
			
			if nivel is not None:
				proxies_clasificados.append((categoria, ip, puerto, nivel))
			
			if completados % 100 == 0 or completados == total:
				print(f"{gris}Progreso: {completados}/{total}{reset}")
	
	ruta_clasificados = ruta_base / "03_PROXIES_CLASIFICADOS.txt"
	with open(ruta_clasificados, "w", encoding="UTF-8") as archivo:
		categoria_previa = None
		for categoria, ip, puerto, nivel in sorted(proxies_clasificados):
			if categoria != categoria_previa:
				archivo.write(f"# {categoria}\n")
				categoria_previa = categoria
			archivo.write(f"{ip}:{puerto},{nivel}\n")
	
	print(f"\n{verde_brillante}Clasificados: {len(proxies_clasificados)} de {total}{reset}")
	print(f"{verde_brillante}[+] Guardado en:{reset} {ruta_clasificados}")
	
	resumen_por_categoria(proxies_clasificados)
	
	return proxies_clasificados

def resumen_por_categoria(proxies_clasificados):
	conteo = {}
	for categoria, ip, puerto, nivel in proxies_clasificados:
		conteo.setdefault(categoria, {"Transparente": 0, "Anonimo": 0, "Elite": 0})
		conteo[categoria][nivel] += 1
	
	print(f"\n{cian_brillante}--- Resumen por categoría ---{reset}")
	for categoria in sorted(conteo.keys()):
		niveles = conteo[categoria]
		total_categoria = sum(niveles.values())
		print(f"{amarillo_brillante}{categoria}{reset} ({total_categoria} total):")
		print(f"  {rojo_brillante}Transparente:{reset} {niveles['Transparente']}   "
			  f"{amarillo_brillante}Anonimo:{reset} {niveles['Anonimo']}   "
			  f"{verde_brillante}Elite:{reset} {niveles['Elite']}")


def menu_principal():
	while True:
		try:
			print("------------MENU PROXYS------------")
			print("1 - Cargar y Descargar Listas")
			print("2 - Procesar Proxies")
			print("0 - Salir de la Aplicación")
			
			opcion = int(input("\nElija Una Opción Válida: "))
			
			if opcion == 1:
				cargar_lista()
				descargar_archivos()
			elif opcion == 2:
				print("\n2. Procesar Proxies:")
				print(f"{rojo_brillante}   ├──{reset} {amarillo_brillante}1.{reset} Chequear conectividad (socket)")
				print(f"{rojo_brillante}   ├──{reset} {amarillo_brillante}2.{reset} Probar funcionalidad real (requests)")
				print(f"{rojo_brillante}   ├──{reset} {amarillo_brillante}3.{reset} Clasificar nivel de anonimato")
				print(f"{rojo_brillante}   └──{reset} {amarillo_brillante}4.{reset} Volver al menú principal\n")
				opcion_2 = int(input("Escoja opción de submenú: "))
				if opcion_2 == 1:
					chequear_conectividad()
				elif opcion_2 == 2:
					probar_funcionalidad()
				elif opcion_2 == 3:
					clasificar_proxies()
			elif opcion == 0:
				print("Saliendo...")
				break
		except ValueError:
			print("Error. Opción Inválida.")


menu_principal()
