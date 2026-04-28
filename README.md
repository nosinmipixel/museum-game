[![es](https://img.shields.io/badge/lang-es-yellow.svg)](README.es.md)

# 🎮 General Synopsis

Simulation game that combines quiz questionnaires and is set in the Prehistory Museum of Valencia.

![Game Screenshot](https://lh3.googleusercontent.com/pw/AP1GczOKMVR9QVdBP-oWwythcRhdXk_5Wzd3YUS0zcL3BkLVDwsd3Chw-X5tK_UHX9_hC6O2KLJpVGwgg8iQMEYDVUnpcO4v6M0Gzy0F7dlg0TFTYNZMjX7LyvfMa2uc3Ybtt8Ltty7ZaUIwMl5qFKpX7SKT=w1280-h720-s-no)

The player acts as the "rookie" curator of a museum who can increase their experience by completing a series of tasks:
- Organizing the museum's collection.
- Assessing the material condition of objects.
- Monitoring environmental conditions in the building, as well as dealing with pest threats.
- Assisting researchers, students, and the general public.

Completing these tasks will allow the player to reach the position of museum director. However, situations may arise that complicate achieving this goal.

# 💻 Development

Game developed with UPBGE (https://upbge.org)

The game was initially developed with UPBGE 0.44. However, alpha version 0.1 has been developed in UPBGE 0.36 to achieve better performance.

Developer documentation can be found in the `Docs` folder.

# 🚀 Installation

1. Download the game version corresponding to your operating system (Currently, versions are available for Linux and Windows)
2. Extract the `.zip` or `.tar.gz` file on your computer.
3. Open the game launcher executable: `.sh` (Linux) or `.exe` (Windows)

# 🚀 Creating an Executable

You can create your own executable from the source code. To do so:

1. Download and install UPBGE version 0.36.1 (https://github.com/UPBGE/upbge/releases)
2. Open the `Intro_Game.blend` file in UPBGE and make sure you have enabled the option to export an executable: `Edit > Preferences > Add-ons > Import-Export: Save As Game Engine Runtime`
3. Once this option is enabled, you can create the executable: `File > Export > Save as game runtime`

# 📦 Downloads

- [[Windows](https://mega.nz/file/sy8UlarK#ZPZlE4dc7CEKrPhj6XtWJBs3a7DSpyhXSJvpgJ6J8C0)](releases)
- [[Linux](https://mega.nz/file/tjtinaaA#L8zGqQLEft6LJZaDOTAQwCRdiLp0G_Vi8kW1PlOR5Y4)](releases)
- [Source Code](https://github.com/nosinmipixel/museum-game)

# 📜 License

- Code and .blend files: GPL 3.0
- Assets: See `ASSETS_LICENSE.md`
- AI Disclosure: See `AI_DISCLOSURE.md`

# 🎮 Keyboard Shortcuts and Mouse Controls

- `W`, `S`, `A`, `D` keys or arrow keys to move the player.
- `P` or `Esc` keys to pause the game and open the main menu.
- `I` key to open the object inventory.
- `Z` key to toggle the player's X-Ray vision mode.
- Left mouse click on objects and characters to interact with them.
- Right mouse click to activate the spray can.

# 📜 Instructions

Start by exploring the museum to familiarize yourself with the spaces and elements. The world size is relatively small and will allow you to move quickly through each of the main areas:
- The Exhibition Halls.
- The Restoration Laboratory.
- The Reception Area.
- The Storage Rooms.
- The Library.

![Museum Map](https://lh3.googleusercontent.com/pw/AP1GczMnGGm_sZxsJJ6bAz_zb4JQCvDktms6qzbCdAMkKXpOOBrdw7Tgos8FmBVt174HdDQBmIbHQNrUHmBe5UutOrcS930ezDyaSOsC8mWymTiQb5zSjxhhZtB8C1GBYi73bmQP6Cmp_BnVwfQsF-tJCrNe=w1280-h720-s-no?authuser=0)

From time to time, certain tasks will appear that we must complete if we want to level up:

## Reception, Storage, and Cataloging

The first task consists of collecting archaeological objects in the museum's Reception Area, restoring them in the Restoration Laboratory (not all objects require restoration), and then storing them in the Storage Rooms on the appropriate shelf.

![Intake Area](https://lh3.googleusercontent.com/pw/AP1GczOa3tgO7OW1tsOjQGn8B4B7wBKsl1G-_uqoSja4TfPO_d1H03avLHjaoKiYCkKxq6yisi2x1OOdoDndyWhPTtP9jgxK73PuvhhvJCy6wMv8w1G0jjZtMiPCSSAcVU1aoLEfunZB1m81PV9iuWOBThFW=w1280-h720-s-no?authuser=0)

You can check the condition of objects by pressing the `I` key (Inventory). This window also displays more information about the object itself.

If the object does not require restoration or has already been restored, you can then go to the Storage Rooms to store it on one of the shelves.

Not all shelves have sufficient space, nor are they suitable for every object. Each shelf is assigned to house objects from one of these five periods: Paleolithic, Neolithic, Bronze Age, Iberian period, and Roman period.

![Storage Rooms](https://lh3.googleusercontent.com/pw/AP1GczP4PThOEJEoZ-Nlvh4ZwEDlYtmVDAbDJTiyjwxkdkcI2E8taXV_vm8Z9Qt7qyQ3Oy7AAeddLRkUaG_-1vuIBlvLRwWRhCop57jTiDDPrM8wkhtiMkmm-E3Cgg1bhW91xniLMalqpiK7LngDrcelz_Bv=w1280-h720-s-no?authuser=0)

`*`Inventory Window 1

![Inventory 1](https://lh3.googleusercontent.com/pw/AP1GczNQxmQmrA7KG8nccpcpKdOQjJ3fqgBBQfN-VlIGfSwe-YhgesIlGYxedBhR8lDn3mj8lPJrrXmYQwZXLpi19xj_uSDnWFiLCTHcmv7qGfTY4Fs3sL_u357P5-8vaHsOfHmAcYsHKAJzLyQGoBbay6u4=w1280-h720-s-no?authuser=0)

`*`Inventory Window 2

![Inventory 2](https://lh3.googleusercontent.com/pw/AP1GczMc6xcMagyZKgUYlx40ItaHCi8HZa2TkX8ATRGXIUVJVKBNnGCpqwNzCVqPVQiAnbx8bJdgPPZ-E1r7qPgl4TuKVfo1MPhjie9AUhJ7T1lsmUAZRdz-Dy4S8KPU3eccoVXG8NM1WVIao9N4ahv4rC_x=w1280-h720-s-no?authuser=0)

To interact with a shelf, approach it and click on it. If you are at the correct shelf, the inventory card for the piece will appear, allowing you to store it there.

![Shelf Interaction](https://lh3.googleusercontent.com/pw/AP1GczNeO_nlYI3d8fEivCZmhHs_oGR8CXboAUeXx4tElMrb61xcw7Haydsl06T1eiPWRueUTrrV7zzEA_4-3QZkchHcaUYob1DbfmPe6Ew9cbDoZMBsQTO8sy64Hy-iyZ7XXrI9pD86Lz7iOfqZoybHSNU7=w1280-h720-s-no?authuser=0)

However, in the Storage Room you may encounter a very unpleasant problem: pests. You must be careful because rodents and insects will try to attack you. You can confront them using an insecticidal spray activated by right-clicking the mouse or pressing the spacebar on the keyboard.

The measurement bars in the bottom left corner will indicate how much health and spray you have. You can replenish your spray by collecting cans at various points throughout the museum. To regenerate health, you will need to locate a first aid kit. If, unfortunately, the bugs defeat you, you will respawn at your starting point.

This pest elimination activity also allows you to gain experience.

Watch your movements: in a museum, controlling environmental conditions is very important, so certain access points are monitored to prevent temperature and relative humidity from spiking. Make sure to close doors at these points.

In addition to your health level, you must also consider your vitality or energy level as the day progresses. This will gradually decrease. However, if you allow the museum's environmental conditions to become inadequate, your mobility will drop very quickly. You will discover that there are places that allow you to recover your energy.

## Restoration

The second major task consists of restoring objects, for which you will need to go to the Restoration Laboratory. There, the restorer will test your knowledge of preventive conservation.

![Restoration Lab](https://lh3.googleusercontent.com/pw/AP1GczMaNFNH_lfISaRKST0rZJAhLqg1tdXRgOB2GCbK_5CGxDqQoz96P6r8i--K-8Ukg82K-RiVX02t5JRLEZ24_XCiNIopc8s8POpIaPTWvG0q6Mb2XFk-FibgZq4fEEUHjs4RnrJtpGnAk7b4jTRSzhIP=w1280-h720-s-no?authuser=0)

Once restored, objects can be stored on their corresponding shelf in the museum's Storage Room.

## Public Assistance

The third major task is assisting researchers, students, and the general public.

From time to time, various people will appear who have questions related to Archaeology or to objects in the museum. If you demonstrate that you have the appropriate knowledge, your skills will increase.

![Public Assistance](https://lh3.googleusercontent.com/pw/AP1GczPun4PV3tAwWTuO7_ZhLPwE1ZwyjpGjCQf6EbwSaxPifyGs7nVXHLrOvjxUhfACtAyOsdq62APdocJzNtCCjCd1-nwuPpgLrfWCd6Qhncvi7cS78lKXDlNn79GIDCEnHYhXK6U5gGBH8LbX_ytPHLeP=w1280-h720-s-no?authuser=0)

Click on characters to interact with them and advance the conversation. Then click on the correct answer or press the corresponding number on the keyboard.

## Other Activities

In addition to these tasks, you can perform other activities such as:

- Visiting the Exhibition Halls and learning about some of the objects. To interact with museum objects, click on them.

![Exhibition Halls](https://lh3.googleusercontent.com/pw/AP1GczNpyX_SardIdnNQTVQlj3HARbdf-zqgg1equI0qrcq7TJ6VprBf0LnbnhORMZkdXemDqK58UPtd6-Jk9jZKDIzRVx5fj7wp2GW_8cW5SReMDIq74nmYdlGqF4Y2Q5uni-JvIgkympWMbNhpSv7wyajr=w1280-h720-s-no?authuser=0)

- Additionally, you can consult specialized manuals and books in the museum's Library. This is useful if you have doubts about any of the game's questions; here you can find information that will help you solve them. Approach the bookshelves and check their subject matter. When you click on the books, their content will be displayed in a new window. You can navigate through the book's content using the corresponding navigation buttons.

![Library](https://lh3.googleusercontent.com/pw/AP1GczNrQmQPmn2UXIgx7NpD0WcDaEuf6l1a0cpLjHYnOfXfrCMpseaG9ECmEbY2hUR9qqkdKjTYTSmKRqNrD9o3kJa7qxgcI57yCMTX8KufguO5heduGarSOQRdRWBPHM7OchHpY8M8IhdRixh9lEzO-vTD=w1280-h720-s-no?authuser=0)

- You can also make new friends who will help you in your work.

![Friends](https://lh3.googleusercontent.com/pw/AP1GczOh3Fn102chNaD2koTdZVaLUjvnAPIJyQVOLy-avdrByNEZVxA1oBT0RtCc2-q0E2Gtr6ZrpRnYWMA5X_xwlkQS9xWZMYbevDTueJsL80Ka3ZuOuxU-qjNKYxdFxpPBgNf0ZrcQMFJhF0b_ZgZio9kf=w1280-h720-s-no?authuser=0)
