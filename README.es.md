# Raiz -- Las raices ven lo que la superficie esconde

Raiz es un agente de justicia ambiental con inteligencia artificial. Conecta datos ambientales fragmentados en una sola imagen y los pone en manos de las comunidades que mas los necesitan.

Un codigo postal. Un comando. Todo lo que necesitas para defender tu comunidad.

---

## Por que existe Raiz

En febrero de 2025, el gobierno federal de Estados Unidos elimino EJSCREEN y CEJST -- las dos herramientas principales de evaluacion de justicia ambiental. Las comunidades que dependian de estas herramientas para luchar contra permisos y presentar comentarios regulatorios perdieron sus datos de un dia para otro.

Mientras tanto:
- Las acciones de cumplimiento de la EPA siguen en declive
- La autodeclaracion es la norma -- los contaminadores califican su propia tarea
- Los permisos de nuevas instalaciones se registran en bases de datos estatales con minimo aviso publico
- Las responsabilidades ambientales corporativas estan enterradas en documentos de la SEC que nadie lee
- Los monitores de calidad del aire de la EPA son escasos en barrios de bajos ingresos
- Las comunidades que respiran el peor aire son las que menos datos tienen

Raiz reconstruye lo que fue eliminado y agrega lo que nunca existio: investigacion, prediccion y accion -- todo en una sola herramienta.

---

## Pruebalo ahora mismo

```bash
git clone https://github.com/Liberation-Labs-THCoalition/Project-Raiz.git
cd Project-Raiz
python -m raiz query 62701 --demo --actions
```

Veras un informe ambiental completo: instalaciones, violaciones, emisiones toxicas, calidad del aire, datos demograficos, rendicion de cuentas corporativa y acciones sugeridas. Todo a partir de un codigo postal.

---

## Que encuentra Raiz

Cuando consultas un codigo postal, Raiz extrae datos de seis fuentes simultaneamente:

### Instalaciones y violaciones (EPA ECHO)
Cada instalacion regulada -- Clean Air Act, Clean Water Act, RCRA. Cada inspeccion, violacion y accion de cumplimiento. Si alguien fue realmente sancionado o no.

### Emisiones de quimicos toxicos (EPA TRI)
Cada libra de quimicos toxicos liberados al aire, agua o suelo. Cuales son cancerigenos conocidos. Quien los esta liberando.

### Calidad del aire (AirNow + PurpleAir)
Monitores oficiales de la EPA *y* sensores comunitarios. Cuando el monitor mas cercano de la EPA esta a 10 millas pero hay un sensor PurpleAir en la siguiente cuadra, Raiz te lo dice -- y senala la brecha de monitoreo.

### Datos demograficos (US Census)
Raza, ingresos, tasa de pobreza, ninos menores de 5 anos, adultos mayores de 65, cobertura de seguro medico. Indicadores de justicia ambiental detectados automaticamente: comunidad mayoritariamente de minorias, bajos ingresos, alta poblacion infantil.

### Rendicion de cuentas corporativa (SEC EDGAR)
Los reportes 10-K y 10-Q de la empresa matriz. Reservas de remediacion ("sabemos que estamos contaminando y reservamos $4.2 millones para limpieza"). Decretos de consentimiento. Designaciones Superfund. Multas declaradas.

### Puntaje de riesgo
Todo lo anterior combinado en un puntaje de riesgo ambiental comunitario de 0 a 10. Violaciones + cero multas = brecha de cumplimiento. Cancerigenos + comunidad mayoritariamente de minorias + ninos = el numero que incomoda a los legisladores.

---

## El analisis de disparidad

Raiz no solo reporta lo que pasa en una comunidad. Compara dos comunidades lado a lado:

```
Comunidad A: 62701
  74% personas de color | Ingreso medio: $28,400

Comunidad B: 62704
  12% personas de color | Ingreso medio: $78,500

Comparacion de carga ambiental:
  Violaciones (3 anos)          : A=       47  B=        2  ratio=23.5x  DISPARIDAD
  Emisiones toxicas al aire (lbs): A=   50,000  B=    1,200  ratio=41.7x  DISPARIDAD
  Cancerigenos liberados        : A=        5  B=        0  ratio=inf    DISPARIDAD

HALLAZGO: La comunidad con 74% de personas de color soporta 41.6x
la carga ambiental de la comunidad con 12% de personas de color.
Este patron es consistente con racismo ambiental.
```

Numeros que hacen visible lo invisible.

---

## El vigilante de permisos

Raiz vigila nuevos permisos ambientales cerca de las comunidades que te importan. Cuando aparece uno:

1. **Lo detecta** -- nueva solicitud de permiso detectada dentro de 3 millas
2. **Investiga** -- obtiene el historial de violaciones del solicitante en todas sus instalaciones
3. **Mapea el impacto** -- datos demograficos, carga existente, escuelas cercanas
4. **Sigue el dinero** -- revisa los documentos de la SEC de la empresa matriz
5. **Genera la respuesta** -- un comentario publico listo para presentar con cada dato relevante citado
6. **Vigila el plazo** -- cuenta regresiva para la fecha limite de comentarios

La comunidad no tiene que buscar el permiso. El permiso encuentra a la comunidad.

---

## Automatizacion de FOIA

Cuando Raiz encuentra violaciones sin registros de inspeccion, o permisos sin documentacion publica, genera solicitudes de la Ley de Libertad de Informacion (FOIA):

- Carta lista para firmar con todos los elementos legalmente requeridos
- Dirigida a la agencia correcta (estatal o federal)
- Solicita exencion de tarifas (estandar de interes publico)
- Registra la fecha limite legal de respuesta
- Senala obstruccion cuando las agencias no responden a tiempo

La persona firma la carta. Raiz recuerda la fecha limite.

---

## Como empezar

### Para organizaciones comunitarias

```bash
# Instalar
git clone https://github.com/Liberation-Labs-THCoalition/Project-Raiz.git
cd Project-Raiz
pip install aiohttp

# Consultar tu comunidad (modo demo -- no necesitas claves de API)
python -m raiz query TU_CODIGO_POSTAL --demo --actions

# Con datos reales (claves de API gratuitas)
python -m raiz query TU_CODIGO_POSTAL --airnow-key TU_CLAVE --actions
```

### Claves de API (todas gratuitas)

| Fuente | Requiere clave? | Donde obtenerla |
|--------|:---------------:|-----------------|
| EPA ECHO | No | API abierta |
| EPA TRI | No | API abierta |
| AirNow | Si (gratuita) | [docs.airnowapi.org](https://docs.airnowapi.org) |
| PurpleAir | Si (gratuita) | [community.purpleair.com](https://community.purpleair.com) |
| Census | Opcional | [api.census.gov](https://api.census.gov/data/key_signup.html) |
| SEC EDGAR | No | API abierta (instalar `edgartools`) |

### Dependencias opcionales

```bash
pip install edgartools    # Busqueda de documentos corporativos de la SEC
pip install geopandas     # Analisis geografico y mapas
pip install folium        # Mapas interactivos
```

---

## Lo que viene

La Fase 1 de Raiz es una herramienta de consulta -- preguntas y te responde. La Fase 2 la convierte en un agente que vigila mientras duermes:

- **Rastreadores de permisos estatales** -- monitoreo automatizado de las 50 bases de datos estatales de permisos ambientales
- **Prediccion de violaciones** -- modelo de aprendizaje automatico entrenado con historial de ECHO para predecir que instalaciones van a violar la ley
- **Red de alertas** -- notificaciones a organizaciones suscritas cuando algo cambia
- **Seguimiento temporal** -- analisis de tendencias para argumentos legales ("3 anos consecutivos de violaciones en aumento")
- **Panel web** -- interfaz en navegador para personas sin conocimientos tecnicos
- **Integracion satelital** -- deteccion de vertidos ilegales y emisiones desde imagenes

---

## Privacidad y etica

- **Soberania comunitaria** -- las comunidades afectadas lideran, Raiz apoya
- **Transparencia de datos** -- todos los hallazgos son publicos, todos los metodos son auditables
- **Sin alianzas de greenwashing corporativo** -- Raiz sirve a comunidades, no a contaminadores
- **El racismo ambiental es real y debe nombrarse explicitamente**
- **Codigo abierto** -- las herramientas para defender tu aire y tu agua deben ser gratuitas
- **Verificar antes de alertar** -- las falsas alarmas erosionan la confianza

---

## Construido con

Raiz se apoya en el trabajo de [EDGI](https://github.com/edgi-govdata-archiving) (Environmental Data & Governance Initiative), cuyas herramientas de codigo abierto para acceder a datos de la EPA hicieron esto posible. Construido sobre el [Kintsugi Engine](https://github.com/Liberation-Labs-THCoalition/Project-Kintsugi) por [Liberation Labs / TH Coalition](https://github.com/Liberation-Labs-THCoalition).

---

## Sobre el nombre

*Raiz* es la palabra en espanol para *root* (raiz). Las raices sostienen la tierra, se conectan a redes subterraneas y extraen lo que esta oculto bajo la superficie. La justicia ambiental requiere llegar a la raiz -- sistemica, estructural, subterranea. El nombre honra a las comunidades latinas afectadas desproporcionadamente por la injusticia ambiental.

*Las raices ven lo que la superficie esconde.*
