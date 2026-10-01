# CÓMO ARRANCAR A TRABAJAR — Drakkar

Guía rápida para empezar a programar cada día, y qué hacer cuando algo falla.

---

## 1. Rutina de cada día (3 pasos)

Abrí VS Code en `C:\drakkar` y en la terminal:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

Tiene que aparecer `(venv)` al principio de la línea. Después abrí:

```
http://127.0.0.1:8000/admin/
```

**Con la barra final.** La raíz (`127.0.0.1:8000/`) muestra la página de bienvenida
de Django porque todavía no hay pantallas propias — eso es normal hasta la Semana 2.

Para cortar el servidor: `Ctrl+C`.

---

## 2. Las tres piezas y cómo se relacionan

| Pieza | Qué es | Cómo se enciende |
|---|---|---|
| **PostgreSQL** | Guarda los datos. Es un programa aparte, corre como servicio de Windows. | Solo, al prender el PC |
| **venv** | La carpeta con Django instalado. Son las herramientas. | `.\venv\Scripts\Activate.ps1` |
| **runserver** | El servidor web de desarrollo. | `python manage.py runserver` |

Son independientes. Borrar el venv **no** toca los datos. Apagar PostgreSQL **no**
toca el código. Entender esa separación resuelve el 90% de los sustos.

---

## 3. Problemas frecuentes

### "connection timeout expired" / "could not connect to server"

PostgreSQL no está corriendo.

```powershell
Get-Service postgresql-x64-18
```

Si dice `Stopped`, abrí PowerShell **como administrador** y:

```powershell
Start-Service postgresql-x64-18
```

Si dice `StartType: Disabled`, está prohibido arrancar. Habilitalo:

```powershell
Set-Service postgresql-x64-18 -StartupType Automatic
Start-Service postgresql-x64-18
```

> **Esto ya pasó una vez (30-09-2026).** El servicio estaba deshabilitado y por eso
> PostgreSQL no volvía solo al prender el PC. Si vuelve a pasar, revisá si alguna
> herramienta de "optimización" de Windows lo está desactivando.

**Arranque de emergencia** (si el servicio se niega y necesitás trabajar ya):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\18\data" start
```

Para pararlo después, el mismo comando con `stop`. Ojo: arrancado así **no vuelve
solo** al reiniciar. Es un parche, no la solución.

### "deactivate: el término no se reconoce"

El venv no estaba activado. No es un error: no hay nada que desactivar. Seguí.

### "Failed to create virtual environment" (aviso de VS Code)

Es la extensión de Python de VS Code queriendo crear un venv propio. Si la terminal
funciona, ignoralo. Para que no vuelva:
`Ctrl+Shift+P` → `Python: Select Interpreter` → elegí `.\venv\Scripts\python.exe`

### "Unable to create '.git/index.lock': File exists"

Quedó un archivo huérfano de un comando Git interrumpido. Borralo:

```powershell
Remove-Item C:\drakkar\.git\index.lock
```

### "InconsistentMigrationHistory"

La base tiene migraciones aplicadas en un orden que Django no espera. En desarrollo,
sin datos importantes: borrar la base y migrar de nuevo. Ver D-011.

---

## 4. Tests — antes de cada commit

```powershell
python manage.py test
```

Tiene que terminar en `OK`. Toma menos de un segundo.

Django crea una base temporal (`test_drakkar_dev`), corre las pruebas ahí y la
borra. **Tu base de desarrollo no se toca nunca.**

Para correr solo una parte:

```powershell
python manage.py test stock              # una app
python manage.py test stock.tests.FefoTest   # un grupo
```

### "permission denied to create database"

`drakkar_user` necesita permiso para crear la base temporal:

```
psql -U postgres
```

```sql
ALTER USER drakkar_user CREATEDB;
\q
```

### Cuando un test falla

El mensaje dice qué esperaba y qué obtuvo:

```
AssertionError: None != datetime.date(2026, 12, 2)
in test_los_lotes_sin_fecha_van_al_FINAL
```

Eso significa: un lote sin fecha quedó primero en el orden FEFO. No es un
problema del test — es el modelo roto. Buscá qué cambiaste.

### Qué protegen los 28 tests

| App | Reglas cubiertas |
|---|---|
| `empresas` | constraint de lotes, nombre único por empresa, slug único global, PROTECT al borrar |
| `productos` | código único por empresa, un solo principal, padre y factor juntos |
| `stock` | FEFO con nulos al final, stock como suma de lotes activos, decimales, reporte de vencimientos |

**Al agregar una regla de negocio, agregá su test.** Un test que nunca falla no
sirve: si dudás, rompé el modelo a propósito y comprobá que el test lo detecta.

---

## 5. Después de un `git pull` con cambios de modelos

```powershell
python manage.py migrate
```

Cada base es independiente: hay que correrlo en cada entorno.

---

## 6. Después de instalar un paquete nuevo

```powershell
pip install <paquete>
pip freeze > requirements.txt
```

Y **volver a poner los comentarios** en `requirements.txt` — `pip freeze` los borra.
Ver D-014.

Después, verificá que el archivo no miente:

```powershell
deactivate
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py check
```

Si `check` responde "no issues", `requirements.txt` está completo.

---

## 7. Leer un traceback de Python

1. **Se lee de abajo hacia arriba.** La última línea es el qué; el resto es el camino.
2. **Buscá tu propio archivo.** Entre las líneas de `venv\lib\site-packages\...`
   (código de Django), la que menciona `C:\drakkar\<app>\...` es la tuya. Ahí está
   casi siempre el problema.
3. **Hay errores anidados.** Abajo el original (ej. `psycopg.errors.CheckViolation`),
   arriba cómo lo traduce Django (`IntegrityError`). Es el mismo problema contado
   dos veces. Al escribir código que atrape errores, atrapá el de Django.
4. **Las constraints dicen su nombre.** `viola la restricción «check»
   «local_lotes_requiere_vencimiento»` te dice exactamente qué regla se rompió.

---

## 8. Registros útiles

**PostgreSQL** (por qué no arranca, errores de SQL, conexiones fallidas):

```powershell
Get-Content "C:\Program Files\PostgreSQL\18\data\log\*.log" -Tail 30
```

**Windows** (por qué un servicio no arranca — cuando PostgreSQL ni siquiera
llega a escribir su propio registro):

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'} -MaxEvents 80 |
  Where-Object { $_.Message -like "*postgres*" } |
  Select-Object -First 3 TimeCreated, Message | Format-List
```

> Regla: si el registro de PostgreSQL **no tiene** un intento de arranque de hoy,
> el problema es de Windows, no de PostgreSQL. Mirá el registro de Windows.

---

## 9. Pendiente conocido

El registro de PostgreSQL muestra intentos de conexión fallidos cada 5 segundos
con el usuario `postgres`. Es un programa reintentando con una contraseña vieja
—casi seguro **pgAdmin**— desde tu propia máquina. No es peligroso, pero llena
el registro de ruido y esconde los errores reales. Conviene corregir la contraseña
guardada en pgAdmin o quitar esa conexión.
