[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md)

# 🎮 Sinopsis general
Juego de simulación que combina cuestionarios quiz y está ambientado en el Museo de Prehistoria de Valencia.
![](https://lh3.googleusercontent.com/pw/AP1GczOKMVR9QVdBP-oWwythcRhdXk_5Wzd3YUS0zcL3BkLVDwsd3Chw-X5tK_UHX9_hC6O2KLJpVGwgg8iQMEYDVUnpcO4v6M0Gzy0F7dlg0TFTYNZMjX7LyvfMa2uc3Ybtt8Ltty7ZaUIwMl5qFKpX7SKT=w1280-h720-s-no)
El jugador actúa como el conservador “novato” de un museo que puede aumentar su experiencia si realiza toda una serie de tareas: 
1. Organizar la colección del museo.
2. Evaluar la condición material de los objetos.
3. Vigilar las condiciones ambientales en el edificio, así como enfrentar la amenaza de plagas.
4. Atención a investigadores, estudiantes y público general.

El cumplimiento de estas tareas le permitirá alcanzar la dirección del museo. Sin embargo, pueden surgir situaciones que compliquen la consecución de este logro.

# 💻 Desarrollo
- Juego desarrollado con UPBGE (https://upbge.org)
- El juego se encuentra inicialmente desarrollado con UPBGE 0.44. Sin embargo, la versión alpha 0.1 se ha desarrollado en UPBGE 0.36 para conseguir un mejor desempeño.
- En la carpeta `Docs` se encuentran los documentos para desarrolladores.

# 🚀 Instalación
1. Descarga la versión del juego correspondiente a tu sistema operativo (Actualmente existen versiones para Linux y Windows)
2. Descomprime el archivo `.zip` o .`tar.gz` en tu equipo.
3. Abre el ejecutable de lanzamiento del juego: `.sh` (linux) `.exe` (windows)

# 🚀 Crear ejecutable
Puedes crear tu propio ejecutable a partir de la fuente. Para ello:
- Descarga e instala la versión 0.36.1 de UPBGE (https://github.com/UPBGE/upbge/releases)
- Abre el archivo `Intro_Game.blend` en UPBGE y asegúrate de tener activada la opción de exportar un ejecutable: `Edit > Preferences > Add-ons > Import-Export: Save As Game Engine Runtime`
- Un vez activada esta opción ya puedes crear el ejecutable: `File > Export > Save as game runtime`

# 📦 Descargas
- [[Windows](https://mega.nz/file/sy8UlarK#ZPZlE4dc7CEKrPhj6XtWJBs3a7DSpyhXSJvpgJ6J8C0)](releases)
- [[Linux](https://mega.nz/file/tjtinaaA#L8zGqQLEft6LJZaDOTAQwCRdiLp0G_Vi8kW1PlOR5Y4)](releases)
- [Código fuente](https://github.com/nosinmipixel/museum-game)

# 📜 Licencia
- Código y archivos .blend: GPL 3.0
- Assets: Ver `ASSETS_LICENSE.md`
- Divulgación IA: Ver `AI_DISCLOSURE.md`

# 🎮 Atajos de teclado y uso del ratón
- Teclas W,S,A y D o teclas de dirección para mover al jugador.
- Teclas P o Esc para pausar el juego y abrir el menú principal.
- Tecla I para abrir el inventario de objetos.
- Tecla Z para alternar el modo de visión de X-Ray en el jugador.
- Clic izquierdo de ratón sobre objetos y personajes para interactuar con ellos.
- Clic derecho de ratón para activar el bote de spray. 

# 📜 Instrucciones
Empieza explorando el museo para familiarizarte con los espacios y elementos. El tamaño del mundo es relativamente pequeño y te permitirá desplazarte rápidamente por cada uno de los espacios principales: 
- Las Salas de Exposición.
- El Laboratorio de Restauración.
- La zona de Ingreso.
- Los Almacenes.
- La Biblioteca.

![](https://lh3.googleusercontent.com/pw/AP1GczMnGGm_sZxsJJ6bAz_zb4JQCvDktms6qzbCdAMkKXpOOBrdw7Tgos8FmBVt174HdDQBmIbHQNrUHmBe5UutOrcS930ezDyaSOsC8mWymTiQb5zSjxhhZtB8C1GBYi73bmQP6Cmp_BnVwfQsF-tJCrNe=w1280-h720-s-no?authuser=0)

Cada cierto tiempo aparecerán algunas tareas que debemos realizar si queremos subir de nivel:

## **Ingreso, almacenamiento y catalogación.**
La primera tarea consiste en recoger objetos arqueológicos en la zona de ingreso del museo, restaurarlos en el Laboratorio de Restauración (no todos los objetos necesitan restauración), y luego guardarlos en los Almacenes dentro de la estantería adecuada.
![](https://lh3.googleusercontent.com/pw/AP1GczOa3tgO7OW1tsOjQGn8B4B7wBKsl1G-_uqoSja4TfPO_d1H03avLHjaoKiYCkKxq6yisi2x1OOdoDndyWhPTtP9jgxK73PuvhhvJCy6wMv8w1G0jjZtMiPCSSAcVU1aoLEfunZB1m81PV9iuWOBThFW=w1280-h720-s-no?authuser=0)
Se puede consultar el estado en el que se encuentran los objetos pulsando la tecla I (Inventario). Esta ventana también muestra más información sobre el propio objeto.
Si el objeto no necesita restauración o ya ha sido restaurado, entonces puedes dirigirte a los Almacenes para guardarlo en una de las estanterías.
No todas las estanterías disponen del espacio suficiente, ni son las adecuadas para el objeto. Cada una de ellas está asignada para albergar objetos de cada uno de estos cinco periodos: paleolítico, neolítico, edad del bronce, época ibérica y época romana.
![](https://lh3.googleusercontent.com/pw/AP1GczP4PThOEJEoZ-Nlvh4ZwEDlYtmVDAbDJTiyjwxkdkcI2E8taXV_vm8Z9Qt7qyQ3Oy7AAeddLRkUaG_-1vuIBlvLRwWRhCop57jTiDDPrM8wkhtiMkmm-E3Cgg1bhW91xniLMalqpiK7LngDrcelz_Bv=w1280-h720-s-no?authuser=0)
Ventana 1 del Inventario

![](https://lh3.googleusercontent.com/pw/AP1GczNQxmQmrA7KG8nccpcpKdOQjJ3fqgBBQfN-VlIGfSwe-YhgesIlGYxedBhR8lDn3mj8lPJrrXmYQwZXLpi19xj_uSDnWFiLCTHcmv7qGfTY4Fs3sL_u357P5-8vaHsOfHmAcYsHKAJzLyQGoBbay6u4=w1280-h720-s-no?authuser=0)
Ventana 2 del Inventario

![](https://lh3.googleusercontent.com/pw/AP1GczMc6xcMagyZKgUYlx40ItaHCi8HZa2TkX8ATRGXIUVJVKBNnGCpqwNzCVqPVQiAnbx8bJdgPPZ-E1r7qPgl4TuKVfo1MPhjie9AUhJ7T1lsmUAZRdz-Dy4S8KPU3eccoVXG8NM1WVIao9N4ahv4rC_x=w1280-h720-s-no?authuser=0)
Para interactuar con una estantería, acércate y haz clic sobre ella. Si estás ante una estantería correcta, aparecerá la ficha de inventario de la pieza que te permitirá guardarla en ella.

![](https://lh3.googleusercontent.com/pw/AP1GczNeO_nlYI3d8fEivCZmhHs_oGR8CXboAUeXx4tElMrb61xcw7Haydsl06T1eiPWRueUTrrV7zzEA_4-3QZkchHcaUYob1DbfmPe6Ew9cbDoZMBsQTO8sy64Hy-iyZ7XXrI9pD86Lz7iOfqZoybHSNU7=w1280-h720-s-no?authuser=0)
Sin embargo, en el Almacén puedes encontrarte con un problema muy desagradable: las plagas. Hay que tener cuidado porque los roedores y los insectos intentarán acabar contigo. Puedes enfrentarte a ellos utilizando un spray insecticida que se activa haciendo clic en el botón secundario del ratón o con la barra espaciadora del teclado.

Las barras de medición de la parte inferior izquierda te indicarán cuánta vida y spray tienes. El spray puedes reponerlo recogiendo botes en distintos puntos del museo. Para regenerar la vida tendrás que localizar algún botiquín. Si, por desgracia, los bichos acaban contigo, reaparecerás de nuevo en el punto de origen.

Esta actividad de eliminación de plagas también te permite adquirir experiencia.

Vigila tus desplazamientos: en un museo es muy importante controlar las condiciones ambientales, por lo que se controlan determinados accesos para que la temperatura y la humedad relativa no se disparen. Asegúrate de cerrar las puertas en esos puntos.

Además de la cantidad de vida, también debes tener en cuenta tu nivel de vitalidad o energía conforme avanza el día. Éste irá decreciendo poco a poco. Pero si dejas que las condiciones ambientales del museo no sean las adecuadas, tu movilidad bajará muy rápidamente. Descubrirás que hay sitios que te permiten recuperar tu energía.
 
## **Restauración.**
La segunda gran tarea consiste en restaurar los objetos y para ello tendrás que ir al Laboratorio de Restauración. Allí, la restauradora pondrá a prueba tus conocimientos sobre conservación preventiva.
![](https://lh3.googleusercontent.com/pw/AP1GczMaNFNH_lfISaRKST0rZJAhLqg1tdXRgOB2GCbK_5CGxDqQoz96P6r8i--K-8Ukg82K-RiVX02t5JRLEZ24_XCiNIopc8s8POpIaPTWvG0q6Mb2XFk-FibgZq4fEEUHjs4RnrJtpGnAk7b4jTRSzhIP=w1280-h720-s-no?authuser=0)
Una vez restaurados, los objetos ya pueden ser guardados en su correspondiente estantería del Almacén del museo.

## **Atención al público.**
La tercera gran tarea es la atención a investigadores, estudiantes y público general.
Cada cierto tiempo aparecerán distintas personas que tienen dudas relacionadas con la Arqueología o con objetos del museo. Si demuestras que tienes los conocimientos adecuados, tus habilidades irán en aumento. 
![](https://lh3.googleusercontent.com/pw/AP1GczPun4PV3tAwWTuO7_ZhLPwE1ZwyjpGjCQf6EbwSaxPifyGs7nVXHLrOvjxUhfACtAyOsdq62APdocJzNtCCjCd1-nwuPpgLrfWCd6Qhncvi7cS78lKXDlNn79GIDCEnHYhXK6U5gGBH8LbX_ytPHLeP=w1280-h720-s-no?authuser=0)
Haz clic sobre los personajes para interactuar con ellos e ir avanzando en la conversación. Luego haz clic sobre la respuesta correcta o pulsa el número correspondiente del teclado.

## **Otras actividades.**
Además de estas tareas, puedes realizar otras actividades como:
- Visitar las Salas de exposición y conocer algunos de los objetos. Para interactuar con los objetos del museo haz clic sobre ellos.
![](https://lh3.googleusercontent.com/pw/AP1GczNpyX_SardIdnNQTVQlj3HARbdf-zqgg1equI0qrcq7TJ6VprBf0LnbnhORMZkdXemDqK58UPtd6-Jk9jZKDIzRVx5fj7wp2GW_8cW5SReMDIq74nmYdlGqF4Y2Q5uni-JvIgkympWMbNhpSv7wyajr=w1280-h720-s-no?authuser=0)
- Además, puedes consultar manuales y libros especializados en la Biblioteca del museo. Esto es útil si tienes dudas con alguna de las preguntas del juego, aquí puedes conseguir información que te ayudará a resolverlas. Acércate a las librerías y comprueba su temática. Cuando hagas clic sobre los libros, su contenido se mostrará en una nueva ventana. Puedes desplazarte a través del contenido del libro con los correspondientes botones de navegación.
![](https://lh3.googleusercontent.com/pw/AP1GczNrQmQPmn2UXIgx7NpD0WcDaEuf6l1a0cpLjHYnOfXfrCMpseaG9ECmEbY2hUR9qqkdKjTYTSmKRqNrD9o3kJa7qxgcI57yCMTX8KufguO5heduGarSOQRdRWBPHM7OchHpY8M8IhdRixh9lEzO-vTD=w1280-h720-s-no?authuser=0)
- También puedes hacer nuevos amigos que te ayudarán en tu trabajo.
![](https://lh3.googleusercontent.com/pw/AP1GczOh3Fn102chNaD2koTdZVaLUjvnAPIJyQVOLy-avdrByNEZVxA1oBT0RtCc2-q0E2Gtr6ZrpRnYWMA5X_xwlkQS9xWZMYbevDTueJsL80Ka3ZuOuxU-qjNKYxdFxpPBgNf0ZrcQMFJhF0b_ZgZio9kf=w1280-h720-s-no?authuser=0)
