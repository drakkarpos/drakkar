# Raspberry Pi — montaje y configuración

Servidor de Drakkar en la fase Pi. Una sola Pi atiende a todos los locales (D-016).

**Montada:** 2026-10-01

---

## 1. Hardware

| Pieza | Detalle |
|---|---|
| Placa | Raspberry Pi 4, 8 GB |
| Almacenamiento | Netac Portable SSD Z6s, 232 GB, por USB 3 |
| Alimentación | Fuente oficial de Raspberry Pi |
| Sistema | Raspberry Pi OS Lite 64-bit (base Debian trixie) |
| Sin tarjeta SD | La Pi arrancó directo desde el SSD |

**Por qué SSD y no tarjeta SD:** una tarjeta SD tiene escrituras limitadas por
celda, y una base de datos escribe constantemente — cada venta, cada ajuste, más
su registro interno (WAL). El patrón conocido es que la Pi anda bien unos meses
y después empieza a corromperse. Con un cliente real trabajando, eso es pérdida
de datos y de ventas.

---

## 2. Datos de red

| | |
|---|---|
| Nombre | `drakkar` → se alcanza como `drakkar.local` |
| IP (2026-10-01) | `192.168.1.84` |
| MAC | `e4:5f:01:42:f6:7c` |
| Conexión actual | **WiFi** — hay que pasarla a cable antes de producción |
| Rango DHCP del router | `192.168.1.81` – `192.168.1.219` |

Conexión desde Windows:

```powershell
ssh drakkar@drakkar.local
ssh drakkar@192.168.1.84      # si el nombre no resuelve
```

Si `ping drakkar.local` responde con una dirección IPv6 (`fe80::...`) y no se
consigue la IPv4, buscarla por la MAC:

```powershell
arp -a | findstr "e4-5f-01"
```

**Pendiente:** reservar la IP en el router. El menú del router no mostró la
opción de reserva DHCP en la pantalla de dispositivos; hay que seguir buscando o
asignar una IP fuera del rango DHCP desde la Pi.

---

## 3. EL PROBLEMA QUE COSTÓ UNA TARDE — UAS

### Síntoma

La Pi funcionaba, y de golpe **todos los comandos dejaban de existir**:

```
-bash: ls: command not found
-bash: ip: command not found
-bash: dpkg: command not found
```

La sesión SSH seguía viva y bash respondía, pero nada que hubiera que leer del
disco funcionaba.

### Cómo se diagnostica

Con `ls` roto no se puede investigar con herramientas normales. Lo que sí
funciona es la expansión de comodines, que la hace bash sin leer el disco:

```bash
echo /bin/*
```

- Devuelve una lista → el disco se lee, el problema es otro
- Devuelve literalmente `/bin/*` → **el disco no se puede leer**

En nuestro caso devolvió `/bin/*`. El sistema estaba vivo solo en memoria.

### La causa

USB 3.0 trae un protocolo llamado **UAS**, más rápido. La Raspberry Pi 4 no se
lleva bien con la implementación de UAS de muchos adaptadores USB-SATA: el disco
funciona un rato y bajo escritura intensa se desconecta.

Se confirma con:

```bash
lsusb -t
```

Si la línea del disco dice `Driver=uas`, es esto.

### El arreglo

Obtener el identificador del disco:

```bash
lsusb
```

```
Bus 002 Device 002: ID 0dd8:0562 Netac Technology Co., Ltd Netac Portable SSD Z6s
                       ^^^^^^^^^  ← este
```

Editar el archivo de arranque (con copia de seguridad primero: si queda mal, la
Pi no enciende):

```bash
sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.bak
sudo nano /boot/firmware/cmdline.txt
```

Agregar **al principio de la única línea**, separado por un espacio:

```
usb-storage.quirks=0dd8:0562:u
```

La `u` significa "no usar UAS con este dispositivo". Queda así:

```
usb-storage.quirks=0dd8:0562:u console=serial0,115200 console=tty1 root=PARTUUID=5bef2fd2-02 rootfstype=ext4 fsck.repair=yes rootwait ds=nocloud;i=rpi-imager
```

> **Todo en UNA línea, sin ningún Enter.** El `>` que muestra nano al final del
> renglón no es parte del texto: indica que la línea sigue fuera de la pantalla.

Guardar (`Ctrl+O`, `Enter`, `Ctrl+X`) y reiniciar:

```bash
sudo reboot
```

### Comprobación

```bash
lsusb -t
```

Tiene que decir `Driver=usb-storage` y seguir a `5000M` (velocidad USB 3).

```
Port 002: Dev 002, If 0, Class=Mass Storage, Driver=usb-storage, 5000M
```

Se pierde algo de rendimiento y se gana estabilidad. Para una base de datos, el
cambio es obvio.

### Si la Pi no arranca después de editar

La partición de arranque es FAT32 y **Windows la puede leer**. Enchufar el SSD
al PC, abrir la unidad chica que aparece, borrar `cmdline.txt` y renombrar
`cmdline.txt.bak` a `cmdline.txt`. Vuelve a como estaba.

### Si se cambia de disco o de Pi

**Este arreglo es específico de este modelo de SSD.** Con otro disco hay que
repetir el diagnóstico: `lsusb -t`, y si dice `uas`, el mismo procedimiento con
su propio identificador.

Conviene aplicar el quirk **antes del primer arranque**, editando `cmdline.txt`
desde Windows en cuanto termina de grabarse la imagen. Así el disco nunca pasa
por el problema.

---

## 4. Lo que falta antes de producción

- [ ] **Pasar de WiFi a cable.** El WiFi en el servidor afecta a todos los
      locales a la vez cuando falla
- [ ] **UPS** para la Pi y el router. La Pi consume poquísimo; un UPS chico da
      horas y cubre los cortes breves, que son la mayoría
- [ ] Reservar la IP en el router
- [ ] Instalar PostgreSQL (Día 29)
- [ ] Gunicorn como servicio que arranque solo al encender (Día 29)
- [ ] Cloudflare Tunnel (Día 29)
- [ ] Backups automáticos (Día 7, pendiente)

---

## 5. Reglas aprendidas

**Si faltan comandos básicos, no faltan paquetes: falta el disco.** `ls` es de
lo más elemental que tiene un Linux. Que no exista significa que el sistema no
puede leer el almacenamiento.

**Nunca abrir puertos en el router.** La pantalla del router ofrece
"Configurar tus puertos": eso expondría la Pi a internet entero y empezarían a
llegar intentos de intrusión en minutos. Cloudflare Tunnel resuelve el acceso
remoto sin abrir nada — la Pi sale a conectarse, no recibe conexiones.

**La Pi es un punto único de fallo** mientras dure esta fase. Ver D-016.
