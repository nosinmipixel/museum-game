```mermaid

graph LR
  %% Definición de estilos por categoría
  classDef core fill:#bbdefb,stroke:#1565c0,stroke-width:2px,color:#000
  classDef ui fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px,color:#000
  classDef npc fill:#ffe0b2,stroke:#e65100,stroke-width:2px,color:#000
  classDef inv fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000
  classDef mech fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
  classDef snd fill:#b3e5fc,stroke:#0277bd,stroke-width:2px,color:#000
  classDef quiz fill:#f8bbd0,stroke:#c2185b,stroke-width:2px,color:#000
  classDef util fill:#eeeeee,stroke:#616164,stroke-width:2px,color:#000

  subgraph Core["📦 Core & Global"]
    GD[game_data.py<br/><i>Singleton / Truth</i>]:::core
    GA[game_access.py<br/><i>Access Facade</i>]:::core
    SS[save_system.py<br/><i>JSON Persistence</i>]:::core
    GI[game_init.py<br/><i>Welcome/Init</i>]:::core
    IG[init_game.py<br/><i>Engine Boot</i>]:::core
    GAc[game_achievements.py<br/><i>Progress/Rewards</i>]:::core
    GDis[game_displace_objects.py<br/><i>Slot Manager</i>]:::core
    
    GA --> GD
    GI --> GD
    IG --> GD
    SS --> GD
    GAc --> GD
    GDis --> GD
  end

  subgraph UI["🖥️ UI & HUD"]
    BLF[BLF_module.py<br/><i>Text Renderer</i>]:::ui
    IQ[info_queue.py<br/><i>Msg Queue</i>]:::ui
    GT[general_text.py<br/><i>Checklists</i>]:::ui
    FHD[format_hud_data.py<br/><i>Stats Formatter</i>]:::ui
    IS[intro_sequence.py<br/><i>Intro FSM</i>]:::ui
    IT[intro_blf_text.py<br/><i>Intro Text</i>]:::ui
    IB[intro_buttons.py<br/><i>Intro Controls</i>]:::ui
    PW[pause_window.py<br/><i>Pause Menu</i>]:::ui
    PB[pause_buttons.py<br/><i>Pause Controls</i>]:::ui
    DB[death_button.py<br/><i>Restart UI</i>]:::ui
    RB[resize_backgrounds.py<br/><i>Auto-Scaling</i>]:::ui
    BFX[button_fx.py<br/><i>Button FX</i>]:::ui
    EB[exhibition_button.py<br/><i>Close UI</i>]:::ui
    EO[exhibition_objects.py<br/><i>Exhibit Info</i>]:::ui
    MA[message_area_info.py<br/><i>Zone Triggers</i>]:::ui
    ITI[input_toggle_inventory.py<br/><i>Key Toggle</i>]:::ui
    CO[container_object.py<br/><i>Container UI</i>]:::ui

    GT --> IQ --> BLF
    FHD --> BLF
    IS --> IT --> BLF
    IB --> IS
    PW --> PB
    DB --> PW
    RB --> BLF
    BFX --> BLF
    EB --> EO
    MA --> IQ
    ITI --> CO
  end

  subgraph NPC["👾 NPCs & Enemies"]
    NL[npc_logic.py<br/><i>Base Sequencer</i>]:::npc
    ND[npc_dialog.py<br/><i>Dialog System</i>]:::npc
    NLib[npc_librarian.py<br/><i>Librarian</i>]:::npc
    NGuard[npc_security_guard.py<br/><i>Guard</i>]:::npc
    NRL[npc_restoration_logic.py<br/><i>Work Queue</i>]:::npc
    NRD[npc_restoration_dialog.py<br/><i>Restoration Dialog</i>]:::npc
    NCat[npc_cat.py<br/><i>Patrol/Combat</i>]:::npc
    NM[npc_mouse.py<br/><i>Nav/Attack</i>]:::npc
    NC[npc_cockroach.py<br/><i>Damage/Move</i>]:::npc
    NCar[npc_car.py<br/><i>Physics/Move</i>]:::npc
    NPS[npc_pest_spawn.py<br/><i>Wave Spawner</i>]:::npc
    NCF[npc_cat_food.py<br/><i>Feed Items</i>]:::npc

    ND --> NL
    NLib --> ND
    NGuard --> ND
    NRD --> NRL --> NL
    NCat --> NL
    NM --> NL
    NC --> NL
    NCar --> NL
    NPS --> NM
    NPS --> NC
    NCF --> NCat
  end

  subgraph INV["🎒 Inventory & Collectibles"]
    IM[inventory_module.py<br/><i>V1 Manager</i>]:::inv
    IV2[inventory_view2.py<br/><i>V2 Interface</i>]:::inv
    BB[book_buttons.py<br/><i>Book UI</i>]:::inv
    BL[books_library.py<br/><i>Pagination</i>]:::inv
    SO[storage_objects.py<br/><i>Persistence</i>]:::inv
    SSprSp[storage_spawn.py<br/><i>Point Spawner</i>]:::inv
    SCan[spray_can.py<br/><i>Refill Logic</i>]:::inv
    SCSp[spray_can_spawn.py<br/><i>Random Spawn</i>]:::inv
    SPart[spray_particle.py<br/><i>Use Effect</i>]:::inv

    IV2 --> IM
    BB --> BL
    SO --> IM
    SSprSp --> SO
    SCan --> IM
    SCSp --> SCan
    SPart --> SCan
  end

  subgraph MECH["⚡ Mechanics & Environment"]
    PM[player_movement.py<br/><i>Movement/Combat</i>]:::mech
    PD[player_death.py<br/><i>Death/Restart</i>]:::mech
    KH[kit_health.py<br/><i>Healing</i>]:::mech
    KS[kit_stamina.py<br/><i>Stamina Recovery</i>]:::mech
    MEff[matrix_effect.py<br/><i>Particle FX</i>]:::mech
    MRain[matrix_rain_screen.py<br/><i>Screen Overlay</i>]:::mech
    Door[door.py<br/><i>Anim/Proximity</i>]:::mech
    DStreet[door_street.py<br/><i>Auto Doors</i>]:::mech
    Cam[camera.py<br/><i>Smooth Follow</i>]:::mech
    TC[temperature_controller.py<br/><i>Env Sim</i>]:::mech
    SColl[suspend_collections.py<br/><i>UI Lock</i>]:::mech

    PD --> PM
    KH --> PM
    KS --> PM
    MRain --> MEff
    DStreet --> Door
    Cam --> PM
    TC --> PM
    SColl --> IM
  end

  subgraph SND["🔊 Sound & Weather"]
    SBack[sound_background.py<br/><i>Music Manager</i>]:::snd
    SFX[sound_fx.py<br/><i>SFX Engine</i>]:::snd
    SCont[sound_context.py<br/><i>Zone Switch</i>]:::snd

    SFX --> SBack
    SCont --> SBack
  end

  subgraph QUIZ["❓ Quiz & Challenges"]
    QM[quiz_module.py<br/><i>Quiz Engine</i>]:::quiz
    QBL[quiz_button_logic.py<br/><i>Quiz Buttons</i>]:::quiz
    QBR[quiz_button_restoration.py<br/><i>Restoration Quiz</i>]:::quiz
    TCQ[timer_controller.py<br/><i>Quiz Timer</i>]:::quiz

    QBL --> QM
    QBR --> QM
    TCQ --> QM
  end

  subgraph UTIL["🛠️ Utilities & Dev"]
    UE[utils_export_to_folder.py<br/><i>Text Exporter</i>]:::util
    UIF[utils_import_from_folder.py<br/><i>Text Importer</i>]:::util
    UTM[utils_set_test_mode.py<br/><i>Debug Config</i>]:::util
    UPM[utils_set_production_mode.py<br/><i>Release Config</i>]:::util
    EGT[end_game_test.py<br/><i>Endgame Test</i>]:::util
  end

  %% 🔗 Dependencias Cruzadas entre Capas
  BLF --> GA
  IQ --> GA
  NL --> GA
  IM --> GA
  PM --> GA
  SBack --> GA
  QM --> GA
  SO --> SS
  SCan --> SS
  SColl --> GA
  DStreet --> Door --> PM
  MA --> IQ
  ITI --> CO --> IM
  NCF --> NCat
  SCont --> SBack

  %% Renderizado de UI
  IV2 --> BLF
  QM --> IQ
  EO --> BLF
  PW --> BLF
  CO --> BLF
  GT --> GA
  MA --> GA

```

### How to interpret the architectural flow

- **Core (📦):** It is the central core. All systems read/write state through `game_data.py` or `game_access.py`.
- **UI (🖥️):** Renders and formats data. Depends on the Core to read statistics, but does not directly modify game logic.
- **NPCs (👾):** Manages AI and dialogs. Reports progress to the Core and receives spawn/state data.
- **Inventory (🎒):** Handles items and persistence. Communicates with the Core to save/load and with the UI to render.
- **Mechanics (⚡):** Physics, combat, and environment. Heavily depends on the Core and feeds data to the UI (e.g., health/stamina bars).
- **Sound (🔊) and Quiz (❓):** Specialized systems integrated via `game_access.py` and `save_system.py`.
- **Utilities (🛠️):** Development tools. Only interact with the Core for configuration or export.
