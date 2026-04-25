[![en](https://img.shields.io/badge/lang-en-red.svg)](CONTRIBUTING.md)
# 💻 Introducción
- Este juego está desarrollado con UPBGE (https://upbge.org)
- El desarrollo inicial se realizó con la versión UPBGE 0.44. Sin embargo, todo el desarrollo se ha migrado a la versión inferior UPBGE 0.36 para conseguir un mejor desempeño.
- Este juego hace uso de scripts de python y de Logic Bricks. NO se utiliza el sistema de Logic Nodes.

# 💻 Estructura de archivos
Existen dos archivos `.blend` principales:
- `Intro_Game.blend` contiene la escena introductoria del juego. Este es el archivo que debe utilizarse para realizar el ejecutable. Funciones:
> Proporcionar instrucciones de uso y un contexto básico al jugador.
> Realizar la selección inicial de idioma.
> Iniciar una nueva partida.
> Cargar o resetear una partida guardada.
> Lanzar el archivo con la parte principal `Main_Game.blend`.

- `Main_Game.blend` contiene la escena principal del juego que es cargada a través del archivo `Intro_Game.blend`.

La carpeta `Assets` contiene el resto de elementos del juego agrupados por tipo:
- `Fonts`
- `Models`
- `Scripts`
- `Sounds`
- `Texts`
- `Textures`

A excepción de los scripts, el resto de elementos se encuentran vinculados a los archivos `.blend` principales. Esta vinculación se establece desde el propio programa o a través de los scripts.

# 🛠️ Scripts. Aspectos generales
- Los scripts funcionales de python se encuentran incrustados dentro del propio archivo `.blend`.
- Los archivos que se encuentran en la carpeta “/Scripts” del proyecto son una copia de estos archivos incrustados.
- Por tanto, para verificar cualquier cambio en el juego deben actualizarse los archivos que se encuentran en el propio `.blend`. Esto puede hacerse con modificación directa del script en el propio `.blend` o importando los archivos modificados que se encuentran en la carpeta `/Source/Assets/Scripts`. Esta importación puede realizarse utilizando el script: `utils_import_to_folder.py`.
- Al inicio de este proyecto los scripts se encontraban vinculados en el propio archivo  `.blend`. Sin embargo, esta opción quedó descartada porque el control de cambios era menos predecible y en ocasiones no funcionaba correctamente (conflictos). Este control manual permite aplicar los cambios en cualquiera de los sentidos independientemente del flujo de trabajo: Carpeta > `.blend` o `.blend` > Carpeta.
- En función de este flujo de trabajo, los scripts que queden en un lado u otro (carpeta o archivo) podrán considerarse como una copia de seguridad mientras no se sincronicen manualmente a través de las utlidades de importación ( `utils_import_to_folder.py`) o exportación (`utils_export_to_folder.py`)
- Tipos de script:
> Los scripts principales del juego se encuentran asociados al objeto llamado `Game.Controller`. Estos scripts se encargan de gestionar el sistema de ventanas o inventario, visualización de texto a través de BLF, sonido, diálogos, etc.
> Además de los scripts principales, existen scripts que se encuentran asociados a otros objetos y que permiten controlar su comportamiento. Por ejemplo, npcs, libros, objetos de exposición, etc.
> Por último, existen otros scripts que permiten realizar algunas operaciones de utilidad con los archivos como importar o exportar los scripts desde el propio `.blend`.

## 📁 Catálogo de Scripts por Categoría Funcional
`*`Documentación técnica de la arquitectura de código del proyecto`*`

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Blender](https://img.shields.io/badge/Blender-3.6+-orange) ![Status](https://img.shields.io/badge/Status-In%20Development-yellow)

| Categoría Funcional | Script | Descripción |
|---|---|---|
| Núcleo y Global | `game_data.py` | Única fuente de verdad para los datos del juego (estadísticas, estado, inventario). |
| | `game_access.py` | Capa de acceso simplificada a GameManager para el estado del juego. |
| | `game_init.py` | Inicialización del juego con mensajes de bienvenida e información. |
| | `init_game.py` | Inicialización unificada del motor, idiomas y carga del juego. |
| | `save_system.py` | Sistema de guardado y carga de progreso usando archivos JSON. |
| | `game_achievements.py` | Gestión de logros, progreso de coleccionables y recompensas. |
| | `game_displace_objects.py` | Maneja el movimiento de tarjetas del inventario entre ranuras. |
| Interfaz de Usuario (UI) y HUD | `BLF_module.py` | Motor de renderizado de texto, barras de progreso y efectos visuales. |
| | `info_queue.py` | Cola de prioridad para mensajes informativos del HUD. |
| | `general_text.py` | Gestión de texto general y listas de tareas con casillas de verificación. |
| | `format_hud_data.py` | Formateo de datos del HUD y gestión de transiciones de superposición. |
| | `intro_blf_text.py` | Visualización de texto introductorio con soporte multilingüe. |
| | `intro_sequence.py` | Máquina de estados para la secuencia de introducción del juego. |
| | `intro_buttons.py` | Interacción de botones en el menú de introducción. |
| | `pause_window.py` | Gestión del menú de pausa y la interfaz de ajustes. |
| | `pause_buttons.py` | Interacción de botones dentro del menú de pausa. |
| | `death_button.py` | Funcionalidad del botón de reinicio en la pantalla de muerte. |
| | `resize_backgrounds.py` | Escalado de elementos de la UI según la resolución de pantalla. |
| | `button_fx.py` | Sistema de efectos visuales para botones del inventario (V1 y V2). |
| | `exhibition_button.py` | Gestión del botón de cierre para la interfaz de exhibición. |
| | `exhibition_objects.py` | Interacción con objetos de exhibición y visualización de información. |
| | `message_area_info.py` | Mensajes informativos activados por zonas de colisión en el área. |
| | `input_toggle_inventory.py` | Gestión de alternancia del inventario mediante entrada de teclado. |
| | `container_object.py` | Interacción con contenedores y apertura del inventario V2. |
| Sistema de PNJs y Enemigos | `npc_logic.py` | Sistema de activación secuencial y lógica para PNJs base. |
| | `npc_dialog.py` | Sistema de diálogo interactivo para PNJs generales. |
| | `npc_librarian.py` | Control de diálogo y animación para el PNJ Bibliotecario. |
| | `npc_security_guard.py` | Interacción y diálogos para el PNJ Guardia de Seguridad. |
| | `npc_restoration_logic.py` | Lógica del PNJ de Restauración y gestión de cola de trabajo. |
| | `npc_restoration_dialog.py` | Sistema de diálogo específico para el proceso de restauración. |
| | `npc_cat.py` | Comportamiento del PNJ Gato (patrulla, combate y modo mascota). |
| | `npc_mouse.py` | Comportamiento del enemigo Ratón (navegación y ataque). |
| | `npc_cockroach.py` | Comportamiento del enemigo Cucaracha (daño y movimiento). |
| | `npc_car.py` | Control de movimiento y física para el PNJ Coche. |
| | `npc_pest_spawn.py` | Gestor de aparición de plagas (ratones y cucarachas) por oleadas. |
| | `npc_cat_food.py` | Gestión de objetos de comida para el sistema de alimentación del gato. |
| Sistema de Inventario y Coleccionables | `inventory_module.py` | Visualización y gestión de estadísticas para el Inventario V1. |
| | `inventory_view2.py` | Interfaz detallada para gestión de objetos (V2) y restauración. |
| | `book_buttons.py` | Interacción con botones de la interfaz de libros. |
| | `books_library.py` | Carga de contenido, paginación y gestión de libros. |
| | `storage_objects.py` | Gestión y persistencia de objetos coleccionables del mundo. |
| | `storage_spawn.py` | Sistema de aparición de objetos coleccionables en puntos designados. |
| | `spray_can.py` | Interacción con lata de spray para recargas de recursos. |
| | `spray_can_spawn.py` | Control de aparición aleatoria de latas de spray en la escena. |
| | `spray_particle.py` | Sistema de partículas para el efecto de uso del spray. |
| Mecánicas de Juego y Entorno | `player_movement.py` | Mecánicas de movimiento, combate con spray y sistema de resistencia. |
| | `player_death.py` | Gestión de la secuencia de muerte del jugador y reinicio. |
| | `kit_health.py` | Interacción con kit de salud para curación del jugador. |
| | `kit_stamina.py` | Interacción con kit de resistencia para recuperación de energía. |
| | `matrix_effect.py` | Efecto visual de partículas estilo "Matrix" para eventos especiales. |
| | `matrix_rain_screen.py` | Efecto de lluvia de caracteres binarios a pantalla completa. |
| | `door.py` | Interacción con puertas (animación, proximidad y clima). |
| | `door_street.py` | Puertas automáticas de calle controladas por proximidad. |
| | `camera.py` | Control de cámara ortográfica con seguimiento suave del jugador. |
| | `temperature_controller.py` | Simulación de temperatura y humedad basada en el entorno. |
| | `suspend_collections.py` | Suspensión de la lógica de recolección durante interacciones con la UI. |
| Gestión de Sonido y Clima | `sound_background.py` | Sistema de música de fondo con gestión de contexto/zona. |
| | `sound_fx.py` | Sistema centralizado de reproducción de efectos de sonido. |
| | `sound_context.py` | Cambio de contexto musical basado en zonas de colisión. |
| Sistemas de Quiz y Desafíos | `quiz_module.py` | Gestión de preguntas, respuestas y retroalimentación para quizzes. |
| | `quiz_button_logic.py` | Interacción y respuesta de botones para el sistema de quizzes. |
| | `quiz_button_restoration.py` | Interacción específica de botones para el quiz de restauración. |
| | `timer_controller.py` | Control de temporizador para el sistema de quizzes. |
| Utilidades y Herramientas de Desarrollo | `utils_export_to_folder.py` | Exportador de bloques de texto de Blender a archivos físicos. |
| | `utils_import_from_folder.py` | Importador de archivos de texto a bloques de texto de Blender. |
| | `utils_set_test_mode.py` | Configuración de variables para modo de prueba/depuración. |
| | `utils_set_production_mode.py` | Configuración de variables para modo de producción/lanzamiento. |
| | `end_game_test.py` | Script de prueba para verificar el final del juego. |

## 📁 Gráfico nodal con las relaciones entre scripts

Ver el diagrama arquitectónico completo en [`architecture-diagram.md`](architecture-diagram.md).

# 🚀 Flujo de Trabajo (Workflow)
### ➕ Añadir nuevos Assets
1. Prepara tu asset (modelo 3D, textura, sonido, etc.).
2. Colócalo en la carpeta correspondiente dentro de `Source/Assets/` (ej. `Source/Assets/Models/`).
3. Vincula el asset al archivo `.blend` correspondiente (ej. `Main_Game.blend`).

### ➕ Añadir nuevos Scripts
1. Crear tu script dentro del propio archivo `.blend` utilizando cualquier plantilla existente o mediante el botón para crear nuevos bloques de texto. 
2. Al utilizar la herramienta para exportar archivos  `utils_export_to_folder.py`, se creará una copia en la carpeta `Source/Assets/Scripts/` .
3. Asegúrate de que el script sea compatible con la versión de Python de UPBGE que estás usando.

# 📏 Estándares de Código
- **Python**: Utiliza Python 3.x compatible con UPBGE.
- **Nomenclatura**: Mantén una nomenclatura clara y descriptiva para las variables y funciones.
- **Estructura**: Intenta seguir la estructura de scripts ya existente para mantener la consistencia.
- **Comentarios**: Documenta funciones complejas para facilitar la comprensión.

# 📏 Creación de ejecutable
Para crear un ejecutable del juego, asegúrate de tener instalada la versión de UPBGE compatible (se recomienda 0.3 o 0.44 según el caso)
El ejecutable debe realizarse a través del archivo `Intro_Game.blend`.
Asegúrate de tener activado el add-on de exportación en las preferencias de Blender `Edit > Preferences > Add-ons `
Una vez activada esta opción ya puedes crear el ejecutable: `File > Export > Save as game runtime`

# 🧪 Pruebas y Verificación
- Antes de subir cualquier cambio, verifica que el juego se inicia correctamente.
- Asegúrate de que los nuevos assets o scripts no rompan la funcionalidad existente (especialmente los sistemas de inventario y diálogos).
- Comprueba que los cambios en los scripts se han importado correctamente al `.blend`.

# 🤝 Proceso de Contribución
1. **Fork & Clone**: Haz un fork del repositorio y clónalo en tu máquina local.
2. **Branch**: Crea una rama para tu funcionalidad o corrección (`git checkout -b feature/nombre-de-la-mejora`).
3. **Commit**: Realiza commits atómicos y descriptivos.
4. **Push**: Sube tus cambios a tu rama en GitHub.
5. **Pull Request**: Crea un Pull Request detallando los cambios realizados.

