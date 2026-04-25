# end_game_test.py - Versión simplificada para pruebas (CORREGIDA)
import bge
from bge import logic
import game_access

def main():
    cont = logic.getCurrentController()
    owner = cont.owner
    
    # Verificar tecla Ctrl+F9
    keyboard = cont.sensors.get("Keyboard")
    if not keyboard or not keyboard.positive:
        return
    
    f9_pressed = False
    ctrl_pressed = False
    
    for key, status in keyboard.events:
        if key == bge.events.F9KEY and status == bge.logic.KX_INPUT_ACTIVE:
            f9_pressed = True
        elif key in (bge.events.LEFTCTRLKEY, bge.events.RIGHTCTRLKEY) and status == bge.logic.KX_INPUT_ACTIVE:
            ctrl_pressed = True
    
    if not (f9_pressed and ctrl_pressed):
        return
    
    print("\n" + "="*50)
    print("🎮 Ctrl+F9 detectado - FORZANDO FIN DEL JUEGO")
    print("="*50)
    
    # Obtener instancia del juego
    game = game_access.get_game()
    if not game:
        print("❌ Error: No se pudo obtener GameManager")
        return
    
    # FORZAR TAREAS COMPLETADAS
    game.state.task_quiz_total = 7
    game.state.task_quiz = True
    
    game.state.task_restoration_total = 3
    game.state.task_restoration = True
    
    # Crear inventario si no existe
    if not game.state.inventory or "collection_items" not in game.state.inventory:
        game.state.inventory = {
            "collection_items": {
                "pal": [], "neo": [], "bronze": [], "iberian": [], "roman": []
            }
        }
    
    periods = ["pal", "neo", "bronze", "iberian", "roman"]
    game.state.inventory["collection_items"] = {
        "pal": [], "neo": [], "bronze": [], "iberian": [], "roman": []
    }
    
    for i in range(10):
        period = periods[i % 5]
        item_id = i + 1
        item = {
            "item_id": item_id,
            "item_type": period,
            "restored": 2,
            "ubication": 100 + i,
            "exhibition": 0
        }
        game.state.inventory["collection_items"][period].append(item)
    
    game.state.collection_items_total = 10
    game.state.inventoried_items = 10
    game.state.task_storage = True
    
    # Skills
    game.player.skills = 4
    
    # 🔥 FORZAR DETECCIÓN DE FINALIZACIÓN
    # Resetear flag para que se active de nuevo (por si ya estaba activado)
    game.state.game_completed = False
    
    # Llamar a check_tasks_completion para que active los efectos
    result = game_access.check_tasks_completion()
    
    print("✅ Comandos de finalización ejecutados")
    print("📊 Verificar en el log si aparecen los mensajes de activación")