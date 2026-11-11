# DGO Home

A small on-screen home remote for the Linux desktop. The plate follows Cream, Dark, and Glass. Buttons stay paper-white with black type. The selected style fills black with cream type, and Dark stays white with a black ring.

The remote remembers lights, speaker, volume, and the plate on this computer. It does not sign in to an account, and it does not store a device address.

## Install

Needs Python 3, GTK 3, PyGObject, and cairo (`python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0`).

```bash
git clone https://github.com/burnt1983/dgo-home.git
cd dgo-home
bash install.sh
dgo-home
```

Outfit is used when that font is installed. Otherwise the window uses the desktop sans.

Settings are saved in `~/.config/dgo-home/config.json`. It does not start at login.

## How to use it

| Action | What happens |
|---|---|
| Cream, Dark, Glass | Change the plate and the type |
| Transparency | 0 is solid. 100 is clear. Glass stays see-through |
| Speaker, Light, Lamp, Fan | Remember on or off |
| Volume | Remember a level from 0 to 100 |
| Drag the name | Move the window |
| × | Close |

## Uninstall

```bash
bash uninstall.sh
```

## Licence

MIT. See [LICENSE](LICENSE).
