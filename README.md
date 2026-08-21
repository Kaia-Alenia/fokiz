<div align="center">
  <img src="fokiz.svg" alt="Fokiz Logo" width="200" height="200" />
  <h1>Fokiz — Ulysses Contract CLI</h1>
  <p>Fight procrastination with cryptographically immutable commitments, progressive notifications, and anti-cheat heuristics.</p>

  [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)]()
  [![Tests](https://img.shields.io/badge/tests-76%20passed-success.svg)]()
</div>

<p align="center">
  <a href="#english">🇬🇧 English</a> | <a href="#español">🇪🇸 Español</a>
</p>

---

<h2 id="english">🇬🇧 English</h2>

### What is Fokiz?

Fokiz is a CLI tool for Linux that turns work commitments into psychologically binding contracts. It uses a local SQLite database with triggers to enforce immutability, ensuring that once you commit to a task deadline, you cannot change it.

Fokiz is strictly local and offline. No servers, no accounts, no cloud. It uses `systemd --user` for episodic monitoring, waking up every 60 seconds to check your progress and nag you if you are falling behind.

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Immutability** | Contracts cannot be edited once created. Enforced via SQLite triggers. |
| **Fail-closed** | Any integrity doubt causes Fokiz to lock and notify you. |
| **Offline/local** | No network dependencies, no persistent daemons. |
| **No daemon** | The monitor is episodic: systemd launches it every 60s and it exits. |
| **Zero external dependencies** | Just Python 3 stdlib + SQLite. |

### Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/Kaia-Alenia/fokiz/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/Kaia-Alenia/fokiz.git
cd fokiz
python3 install.py
```

### Usage

| Command | Description |
|---------|-------------|
| `fokiz init` | Initializes `~/.local/share/fokiz/` and generates the secret HMAC key |
| `fokiz add` | Creates a new contract interactively |
| `fokiz status` | Lists all active contracts with their metrics |
| `fokiz status --banner` | Shows the full ASCII banner |
| `fokiz done <task_id>` | Completes the current active phase (requires an evidence log) |
| `fokiz surrender <task_id>` | Records capitulation (irreversible) |

### Running Tests

```bash
python3 -m pytest tests/ -v
```

### License

GNU GPL v3 — Copyright (C) Alenia Studios. See [LICENSE](LICENSE) for details.

---

<h2 id="español">🇪🇸 Español</h2>

### ¿Qué es Fokiz?

Fokiz es una herramienta CLI para Linux que convierte compromisos de trabajo en contratos psicológicamente vinculantes: inmutables, verificados criptográficamente y con notificaciones progresivas basadas en el tiempo transcurrido.

Fokiz es local y offline. No necesita servidor, cuenta, nube ni conexión a Internet. Utiliza `systemd --user` para evaluación episódica, despertando cada 60 segundos para vigilar tu progreso.

### Principios de diseño

| Principio | Descripción |
|-----------|-------------|
| **Inmutabilidad** | Los contratos no se pueden editar una vez creados. SQLite lo garantiza vía triggers. |
| **Fail-closed** | Ante cualquier duda de integridad, Fokiz bloquea y notifica. |
| **Offline/local** | Sin dependencias de red, sin daemons persistentes. |
| **No daemon** | El monitor es episódico: systemd lo lanza cada 60 s y termina. |
| **Sin dependencias externas** | Solo Python 3 stdlib + SQLite. |

### Instalación rápida

```bash
curl -sSL https://raw.githubusercontent.com/Kaia-Alenia/fokiz/main/install.sh | bash
```

### Instalación manual

```bash
git clone https://github.com/Kaia-Alenia/fokiz.git
cd fokiz
python3 install.py
```

### Uso

| Comando | Descripción |
|---------|-------------|
| `fokiz init` | Inicializa `~/.local/share/fokiz/` y genera la clave secreta |
| `fokiz add` | Crea un nuevo contrato de forma interactiva |
| `fokiz status` | Lista todos los contratos activos con métricas τ, Δ, zona |
| `fokiz status --banner` | Muestra el banner ASCII completo |
| `fokiz done <task_id>` | Completa la fase activa actual (requiere log de evidencia) |
| `fokiz surrender <task_id>` | Registra capitulación (irreversible) |

### Tests

```bash
python3 -m pytest tests/ -v
```

### Licencia

GNU GPL v3 — Copyright (C) Alenia Studios. Ver [LICENSE](LICENSE) para más detalles.
